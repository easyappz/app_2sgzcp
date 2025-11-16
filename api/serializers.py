from rest_framework import serializers
from .models import Member, Game, GameMove
from django.contrib.auth.hashers import check_password


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=200)
    timestamp = serializers.DateTimeField(read_only=True)


class MemberRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Member
        fields = ['username', 'password']

    def create(self, validated_data):
        member = Member(username=validated_data['username'])
        member.set_password(validated_data['password'])
        member.save()
        return member


class MemberLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        try:
            member = Member.objects.get(username=username)
        except Member.DoesNotExist:
            raise serializers.ValidationError("Неверное имя пользователя или пароль")
        
        if not check_password(password, member.password_hash):
            raise serializers.ValidationError("Неверное имя пользователя или пароль")
        
        data['member'] = member
        return data


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'username', 'elo_rating', 'games_played', 'games_won', 'games_lost', 'games_draw', 'created_at']
        read_only_fields = ['id', 'created_at']


class GameSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    opponent_username = serializers.CharField(source='opponent.username', read_only=True, allow_null=True)
    winner_username = serializers.CharField(source='winner.username', read_only=True, allow_null=True)

    class Meta:
        model = Game
        fields = ['id', 'game_code', 'creator', 'creator_username', 'opponent', 'opponent_username', 
                  'status', 'winner', 'winner_username', 'is_draw', 'current_turn', 'board_state', 
                  'timer_seconds', 'created_at', 'started_at', 'finished_at']
        read_only_fields = ['id', 'game_code', 'created_at', 'started_at', 'finished_at']


class GameMoveSerializer(serializers.ModelSerializer):
    player_username = serializers.CharField(source='player.username', read_only=True)

    class Meta:
        model = GameMove
        fields = ['id', 'game', 'player', 'player_username', 'position', 'symbol', 'move_number', 'timestamp']
        read_only_fields = ['id', 'timestamp', 'move_number']


class CreateGameSerializer(serializers.Serializer):
    timer_seconds = serializers.IntegerField(default=60, min_value=30, max_value=300)


class JoinGameSerializer(serializers.Serializer):
    game_code = serializers.CharField(max_length=10)


class MakeMoveSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=0, max_value=8)


class GameHistorySerializer(serializers.ModelSerializer):
    opponent_username = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ['id', 'game_code', 'opponent_username', 'result', 'finished_at']

    def get_opponent_username(self, obj):
        user = self.context.get('user')
        if obj.creator == user:
            return obj.opponent.username if obj.opponent else None
        return obj.creator.username

    def get_result(self, obj):
        user = self.context.get('user')
        if obj.is_draw:
            return 'Ничья'
        elif obj.winner == user:
            return 'Победа'
        elif obj.winner:
            return 'Поражение'
        return 'Не завершена'


class RatingSerializer(serializers.ModelSerializer):
    position = serializers.IntegerField(read_only=True)

    class Meta:
        model = Member
        fields = ['position', 'username', 'elo_rating', 'games_played', 'games_won', 'games_lost', 'games_draw']