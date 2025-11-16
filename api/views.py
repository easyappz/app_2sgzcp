from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from .serializers import (
    MessageSerializer, MemberRegistrationSerializer, MemberLoginSerializer,
    MemberSerializer, GameSerializer, GameMoveSerializer, CreateGameSerializer,
    JoinGameSerializer, MakeMoveSerializer, GameHistorySerializer, RatingSerializer
)
from .models import Member, Game, GameMove
from django.db.models import Q, F
import jwt
from django.conf import settings
from datetime import datetime, timedelta


class HelloView(APIView):
    """
    A simple API endpoint that returns a greeting message.
    """

    @extend_schema(
        responses={200: MessageSerializer}, description="Get a hello world message"
    )
    def get(self, request):
        data = {"message": "Hello!", "timestamp": timezone.now()}
        serializer = MessageSerializer(data)
        return Response(serializer.data)


def generate_jwt_token(member):
    payload = {
        'user_id': member.id,
        'username': member.username,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def get_member_from_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        member = Member.objects.get(id=payload['user_id'])
        return member
    except (jwt.DecodeError, jwt.ExpiredSignatureError, Member.DoesNotExist):
        return None


class RegisterView(APIView):
    def post(self, request):
        serializer = MemberRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            member = serializer.save()
            return Response({
                'message': 'Регистрация успешна',
                'user_id': member.id,
                'username': member.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = MemberLoginSerializer(data=request.data)
        if serializer.is_valid():
            member = serializer.validated_data['member']
            token = generate_jwt_token(member)
            return Response({
                'token': token,
                'user_id': member.id,
                'username': member.username
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    def get(self, request):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = MemberSerializer(member)
        return Response(serializer.data)


class CreateGameView(APIView):
    def post(self, request):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = CreateGameSerializer(data=request.data)
        if serializer.is_valid():
            game = Game.objects.create(
                creator=member,
                timer_seconds=serializer.validated_data.get('timer_seconds', 60)
            )
            game_serializer = GameSerializer(game)
            return Response(game_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JoinGameView(APIView):
    def post(self, request):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = JoinGameSerializer(data=request.data)
        if serializer.is_valid():
            game_code = serializer.validated_data['game_code']
            try:
                game = Game.objects.get(game_code=game_code, status='waiting')
                if game.creator == member:
                    return Response({'error': 'Нельзя присоединиться к собственной игре'}, status=status.HTTP_400_BAD_REQUEST)
                
                game.opponent = member
                game.status = 'in_progress'
                game.started_at = timezone.now()
                game.save()
                
                game_serializer = GameSerializer(game)
                return Response(game_serializer.data, status=status.HTTP_200_OK)
            except Game.DoesNotExist:
                return Response({'error': 'Игра не найдена или уже началась'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AvailableGamesView(APIView):
    def get(self, request):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        games = Game.objects.filter(status='waiting').exclude(creator=member).order_by('-created_at')
        serializer = GameSerializer(games, many=True)
        return Response(serializer.data)


class GameDetailView(APIView):
    def get(self, request, game_code):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            game = Game.objects.get(game_code=game_code)
            if game.creator != member and game.opponent != member:
                return Response({'error': 'Нет доступа к этой игре'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = GameSerializer(game)
            return Response(serializer.data)
        except Game.DoesNotExist:
            return Response({'error': 'Игра не найдена'}, status=status.HTTP_404_NOT_FOUND)


class MakeMoveView(APIView):
    def post(self, request, game_code):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            game = Game.objects.get(game_code=game_code)
            if game.creator != member and game.opponent != member:
                return Response({'error': 'Нет доступа к этой игре'}, status=status.HTTP_403_FORBIDDEN)
            
            if game.status != 'in_progress':
                return Response({'error': 'Игра не активна'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Определяем символ игрока
            if game.creator == member:
                player_symbol = 'X'
            else:
                player_symbol = 'O'
            
            # Проверяем, чей ход
            if game.current_turn != player_symbol:
                return Response({'error': 'Сейчас не ваш ход'}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = MakeMoveSerializer(data=request.data)
            if serializer.is_valid():
                position = serializer.validated_data['position']
                row = position // 3
                col = position % 3
                
                # Проверяем, что клетка пустая
                if game.board_state[row][col] is not None:
                    return Response({'error': 'Клетка уже занята'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Делаем ход
                game.board_state[row][col] = player_symbol
                move_number = game.moves.count() + 1
                
                GameMove.objects.create(
                    game=game,
                    player=member,
                    position=position,
                    symbol=player_symbol,
                    move_number=move_number
                )
                
                # Проверяем победу
                if check_winner(game.board_state, player_symbol):
                    game.status = 'finished'
                    game.winner = member
                    game.finished_at = timezone.now()
                    update_elo_ratings(game.winner, game.opponent if game.winner == game.creator else game.creator, False)
                # Проверяем ничью
                elif is_board_full(game.board_state):
                    game.status = 'finished'
                    game.is_draw = True
                    game.finished_at = timezone.now()
                    update_elo_ratings(game.creator, game.opponent, True)
                else:
                    # Переключаем ход
                    game.current_turn = 'O' if game.current_turn == 'X' else 'X'
                
                game.save()
                
                serializer = GameSerializer(game)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Game.DoesNotExist:
            return Response({'error': 'Игра не найдена'}, status=status.HTTP_404_NOT_FOUND)


def check_winner(board, symbol):
    # Проверка строк
    for row in board:
        if all(cell == symbol for cell in row):
            return True
    
    # Проверка столбцов
    for col in range(3):
        if all(board[row][col] == symbol for row in range(3)):
            return True
    
    # Проверка диагоналей
    if all(board[i][i] == symbol for i in range(3)):
        return True
    if all(board[i][2-i] == symbol for i in range(3)):
        return True
    
    return False


def is_board_full(board):
    for row in board:
        for cell in row:
            if cell is None:
                return False
    return True


def update_elo_ratings(winner, loser, is_draw):
    K = 32  # Коэффициент изменения рейтинга
    
    if is_draw:
        # При ничьей оба игрока получают/теряют очки в зависимости от разницы рейтингов
        expected_winner = 1 / (1 + 10 ** ((loser.elo_rating - winner.elo_rating) / 400))
        expected_loser = 1 / (1 + 10 ** ((winner.elo_rating - loser.elo_rating) / 400))
        
        winner.elo_rating += int(K * (0.5 - expected_winner))
        loser.elo_rating += int(K * (0.5 - expected_loser))
        
        winner.games_played += 1
        winner.games_draw += 1
        loser.games_played += 1
        loser.games_draw += 1
    else:
        expected_winner = 1 / (1 + 10 ** ((loser.elo_rating - winner.elo_rating) / 400))
        expected_loser = 1 / (1 + 10 ** ((winner.elo_rating - loser.elo_rating) / 400))
        
        winner.elo_rating += int(K * (1 - expected_winner))
        loser.elo_rating += int(K * (0 - expected_loser))
        
        winner.games_played += 1
        winner.games_won += 1
        loser.games_played += 1
        loser.games_lost += 1
    
    winner.save()
    loser.save()


class GameHistoryView(APIView):
    def get(self, request):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        games = Game.objects.filter(
            Q(creator=member) | Q(opponent=member),
            status='finished'
        ).order_by('-finished_at')
        
        serializer = GameHistorySerializer(games, many=True, context={'user': member})
        return Response(serializer.data)


class RatingView(APIView):
    def get(self, request):
        members = Member.objects.filter(games_played__gt=0).order_by('-elo_rating', '-games_won')
        
        # Добавляем позицию каждому игроку
        data = []
        for idx, member in enumerate(members[:100], 1):  # Топ-100 игроков
            serializer = RatingSerializer(member)
            member_data = serializer.data
            member_data['position'] = idx
            data.append(member_data)
        
        return Response(data)


class MyGamesView(APIView):
    def get(self, request):
        member = get_member_from_token(request)
        if not member:
            return Response({'error': 'Не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
        
        games = Game.objects.filter(
            Q(creator=member) | Q(opponent=member)
        ).filter(Q(status='waiting') | Q(status='in_progress')).order_by('-created_at')
        
        serializer = GameSerializer(games, many=True)
        return Response(serializer.data)