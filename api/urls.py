from django.urls import path
from .views import (
    HelloView, RegisterView, LoginView, ProfileView,
    CreateGameView, JoinGameView, AvailableGamesView,
    GameDetailView, MakeMoveView, GameHistoryView,
    RatingView, MyGamesView
)

urlpatterns = [
    path("hello/", HelloView.as_view(), name="hello"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("games/create/", CreateGameView.as_view(), name="create_game"),
    path("games/join/", JoinGameView.as_view(), name="join_game"),
    path("games/available/", AvailableGamesView.as_view(), name="available_games"),
    path("games/my/", MyGamesView.as_view(), name="my_games"),
    path("games/<str:game_code>/", GameDetailView.as_view(), name="game_detail"),
    path("games/<str:game_code>/move/", MakeMoveView.as_view(), name="make_move"),
    path("history/", GameHistoryView.as_view(), name="game_history"),
    path("rating/", RatingView.as_view(), name="rating"),
]