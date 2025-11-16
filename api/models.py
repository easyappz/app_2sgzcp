from django.db import models
from django.contrib.auth.hashers import make_password
import string
import random


class Member(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    elo_rating = models.IntegerField(default=1000)
    games_played = models.IntegerField(default=0)
    games_won = models.IntegerField(default=0)
    games_lost = models.IntegerField(default=0)
    games_draw = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'members'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['elo_rating']),
        ]

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def __str__(self):
        return self.username


class Game(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]
    
    TURN_CHOICES = [
        ('X', 'X'),
        ('O', 'O'),
    ]

    creator = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='created_games')
    opponent = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='joined_games', null=True, blank=True)
    game_code = models.CharField(max_length=10, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    winner = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='won_games', null=True, blank=True)
    is_draw = models.BooleanField(default=False)
    current_turn = models.CharField(max_length=1, choices=TURN_CHOICES, default='X')
    board_state = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    timer_seconds = models.IntegerField(default=60)

    class Meta:
        db_table = 'games'
        indexes = [
            models.Index(fields=['game_code']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.game_code:
            self.game_code = self.generate_game_code()
        if not self.board_state:
            self.board_state = [[None for _ in range(3)] for _ in range(3)]
        super().save(*args, **kwargs)

    def generate_game_code(self):
        length = 6
        characters = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(characters) for _ in range(length))
            if not Game.objects.filter(game_code=code).exists():
                return code

    def __str__(self):
        return f"Game {self.game_code} - {self.status}"


class GameMove(models.Model):
    SYMBOL_CHOICES = [
        ('X', 'X'),
        ('O', 'O'),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='moves')
    player = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='moves')
    position = models.IntegerField()  # 0-8 for 3x3 grid
    symbol = models.CharField(max_length=1, choices=SYMBOL_CHOICES)
    move_number = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'game_moves'
        indexes = [
            models.Index(fields=['game', 'move_number']),
            models.Index(fields=['timestamp']),
        ]
        unique_together = [['game', 'position']]

    def __str__(self):
        return f"Move {self.move_number} in game {self.game.game_code}"