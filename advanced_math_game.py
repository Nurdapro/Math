import pygame
import numpy as np
import random
import asyncio
import platform
import math

# Настраиваем игру
pygame.init()
WIDTH = 800
HEIGHT = 600
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Math Space Adventure")
clock = pygame.time.Clock()

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Шрифты
font = pygame.font.SysFont("Arial", 30)
large_font = pygame.font.SysFont("Arial", 50)

# Звуки
def generate_sound(frequency, duration=0.2):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(2 * np.pi * frequency * t) * 32767
    stereo_audio = np.column_stack((audio, audio)).astype(np.int16)
    return pygame.sndarray.make_sound(stereo_audio)

correct_sound = generate_sound(800)
wrong_sound = generate_sound(200)
bonus_sound = generate_sound(1200)

# Состояния игры
MENU, PLAYING, GAME_OVER = 0, 1, 2
game_state = MENU

# Игрок
player_pos = [WIDTH // 2, HEIGHT - 80]
player_size = 50
player_speed = 8
player_lives = 3
player_score = 0
player_level = 1
game_over_time = 0

# Частицы
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = random.randint(2, 6)
        self.life = random.randint(20, 40)
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self):
        if self.life > 0:
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.size)

# Ответы
class Answer:
    def __init__(self, x, y, value, correct):
        self.x = x
        self.y = y
        self.value = value
        self.correct = correct
        self.size = 35
        self.speed = 1.5 + player_level * 0.2

    def move(self):
        self.y += self.speed

    def draw(self):
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.size, 2)
        text = font.render(str(self.value), True, WHITE)  # Белый текст
        text.set_alpha(255)
        outline = font.render(str(self.value), True, BLACK)  # Чёрная обводка
        screen.blit(outline, (self.x - text.get_width() // 2 - 1, self.y - text.get_height() // 2 - 1))
        screen.blit(outline, (self.x - text.get_width() // 2 + 1, self.y - text.get_height() // 2 + 1))
        screen.blit(outline, (self.x - text.get_width() // 2 - 1, self.y - text.get_height() // 2 + 1))
        screen.blit(outline, (self.x - text.get_width() // 2 + 1, self.y - text.get_height() // 2 - 1))
        screen.blit(text, (self.x - text.get_width() // 2, self.y - text.get_height() // 2))

# Метеориты
class Meteor:
    def __init__(self):
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(-100, -50)
        self.size = 40
        self.speed = 1.5 + player_level * 0.15

    def move(self):
        self.y += self.speed

    def draw(self):
        pygame.draw.circle(screen, (150, 150, 150), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(screen, (100, 100, 100), (int(self.x), int(self.y)), self.size - 5)

# Быстрые метеориты
class FastMeteor:
    def __init__(self):
        self.x = random.choice([50, WIDTH - 50])
        self.y = random.randint(-100, -50)
        self.size = 30
        self.speed_x = random.uniform(-1, 1) + player_level * 0.1
        self.speed_y = 2.5 + player_level * 0.2

    def move(self):
        self.x += self.speed_x
        self.y += self.speed_y

    def draw(self):
        pygame.draw.polygon(screen, (200, 100, 100), [
            (self.x, self.y - self.size),
            (self.x - self.size // 2, self.y + self.size // 2),
            (self.x + self.size // 2, self.y + self.size // 2)
        ])

# Бонусы
class Bonus:
    def __init__(self):
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(-100, -50)
        self.size = 30
        self.speed = 2

    def move(self):
        self.y += self.speed

    def draw(self):
        pygame.draw.polygon(screen, YELLOW, [
            (self.x, self.y - self.size), (self.x + self.size // 2, self.y - self.size // 2),
            (self.x + self.size, self.y), (self.x + self.size // 2, self.y + self.size // 2),
            (self.x, self.y + self.size), (self.x - self.size // 2, self.y + self.size // 2),
            (self.x - self.size, self.y), (self.x - self.size // 2, self.y - self.size // 2)
        ])

# Списки объектов
answers = []
enemies = []
bonuses = []
particles = []

# Операции для уровней
operations = [
    (lambda a, b: a + b, lambda a, b: "{} + {} = ?".format(a, b), lambda a, b: True),
    (lambda a, b: a - b, lambda a, b: "{} - {} = ?".format(a, b), lambda a, b: True),
    (lambda a, b: a * b, lambda a, b: "{} * {} = ?".format(a, b), lambda a, b: True),
    (lambda a, b: a // b, lambda a, b: "{} / {} = ?".format(a, b), lambda a, b: b != 0 and a % b == 0),
    (lambda a, b: a ** b, lambda a, b: "{}^{} = ?".format(a, b), lambda a, b: b < 3),
    (lambda a, b: int(np.sqrt(a)), lambda a, b: "sqrt({}) = ?".format(a), lambda a, b: np.sqrt(a).is_integer()),
    (lambda a, b: b, lambda a, b: "{}*x = {}, x = ?".format(a, a*b), lambda a, b: a != 0),
    (lambda a, b: int(np.log2(a)), lambda a, b: "log2({}) = ?".format(a), lambda a, b: np.log2(a).is_integer()),
    (lambda a, b: math.factorial(a), lambda a, b: "{}! = ?".format(a), lambda a, b: a <= 7)
]

# Генерация вопросов
def generate_question():
    global player_level
    op_idx = min(player_level - 1, len(operations) - 1)
    op_func, question_func, condition = operations[op_idx]
    a = random.randint(1, 10 + player_level * 5)
    b = random.randint(1, 10 + player_level * 2)
    while not condition(a, b):
        a = random.randint(1, 10 + player_level * 5)
        b = random.randint(1, 10 + player_level * 2)
    correct = op_func(a, b)
    question = question_func(a, b)
    wrong1 = correct + random.randint(-10, 10)
    wrong2 = correct + random.randint(-10, 10)
    while wrong1 == correct or wrong2 == correct or wrong1 == wrong2:
        wrong1 = correct + random.randint(-10, 10)
        wrong2 = correct + random.randint(-10, 10)
    positions = random.sample([150, 300, 450, 600], 3)
    answers.clear()
    answers.append(Answer(positions[0], 50, correct, True))
    answers.append(Answer(positions[1], 50, wrong1, False))
    answers.append(Answer(positions[2], 50, wrong2, False))
    return question

current_question = generate_question()

# Настройка игры
def setup():
    global player_pos, player_score, player_lives, player_level, current_question, answers, enemies, bonuses, particles, game_over_time
    player_pos = [WIDTH // 2, HEIGHT - 80]
    player_score = 0
    player_lives = 3
    player_level = 1
    game_over_time = 0
    current_question = generate_question()
    answers.clear()
    enemies.clear()
    bonuses.clear()
    particles.clear()

# Рисуем игрока
def draw_player():
    pygame.draw.polygon(screen, BLUE, [
        (player_pos[0], player_pos[1] - player_size // 2),
        (player_pos[0] - player_size // 2, player_pos[1] + player_size // 2),
        (player_pos[0] + player_size // 2, player_pos[1] + player_size // 2)
    ])
    pygame.draw.rect(screen, WHITE, (player_pos[0] - 10, player_pos[1], 20, 10))

# Рисуем фон
def draw_background():
    for i in range(50):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        pygame.draw.circle(screen, WHITE, (x, y), 1)

# Основной цикл
async def update_loop():
    global game_state, player_pos, player_score, player_lives, player_level, current_question, game_over_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            return

    keys = pygame.key.get_pressed()
    mouse_pos = pygame.mouse.get_pos()
    mouse_clicked = pygame.mouse.get_pressed()[0]

    if game_state == MENU:
        screen.fill(BLACK)
        draw_background()
        title = large_font.render("Math Space Adventure", True, WHITE)
        start_text = font.render("Click to Start", True, WHITE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3))
        screen.blit(start_text, (WIDTH // 2 - start_text.get_width() // 2, HEIGHT // 2))
        if mouse_clicked:
            game_state = PLAYING
            setup()

    elif game_state == PLAYING:
        if keys[pygame.K_LEFT] and player_pos[0] > player_size:
            player_pos[0] -= player_speed
        if keys[pygame.K_RIGHT] and player_pos[0] < WIDTH - player_size:
            player_pos[0] += player_speed

        screen.fill(BLACK)
        draw_background()
        draw_player()

        for answer in answers[:]:
            answer.move()
            answer.draw()
            if answer.y > HEIGHT:
                if answer in answers:
                    answers.remove(answer)
            elif (abs(answer.x - player_pos[0]) < player_size and abs(answer.y - player_pos[1]) < player_size):
                if answer.correct:
                    player_score += 15
                    correct_sound.play()
                    if player_score >= player_level * 60:
                        player_level += 1
                        current_question = generate_question()
                else:
                    player_lives -= 1
                    wrong_sound.play()
                if answer in answers:
                    answers.remove(answer)

        if not answers:
            current_question = generate_question()

        if random.random() < 0.02 + player_level * 0.003:
            enemies.append(random.choice([Meteor(), FastMeteor()]))

        for enemy in enemies[:]:
            enemy.move()
            enemy.draw()
            if enemy.y > HEIGHT:
                if enemy in enemies:
                    enemies.remove(enemy)
            elif (abs(enemy.x - player_pos[0]) < player_size and abs(enemy.y - player_pos[1]) < player_size):
                player_lives -= 1
                if enemy in enemies:
                    enemies.remove(enemy)
                for _ in range(20):
                    particles.append(Particle(player_pos[0], player_pos[1]))

        if random.random() < 0.01:
            bonuses.append(Bonus())

        for bonus in bonuses[:]:
            bonus.move()
            bonus.draw()
            if bonus.y > HEIGHT:
                if bonus in bonuses:
                    bonuses.remove(bonus)
            elif (abs(bonus.x - player_pos[0]) < player_size and abs(bonus.y - player_pos[1]) < player_size):
                player_score += 30
                player_lives = min(player_lives + 1, 5)
                bonus_sound.play()
                if bonus in bonuses:
                    bonuses.remove(bonus)

        for particle in particles[:]:
            particle.update()
            particle.draw()
            if particle.life <= 0 and particle in particles:
                particles.remove(particle)

        question_text = font.render(current_question, True, WHITE)
        screen.blit(question_text, (WIDTH // 2 - question_text.get_width() // 2, 20))
        score_text = font.render(f"Score: {player_score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        lives_text = font.render(f"Lives: {player_lives}", True, WHITE)
        screen.blit(lives_text, (10, 50))
        level_text = font.render(f"Level: {player_level}", True, WHITE)
        screen.blit(level_text, (10, 90))

        if player_lives <= 0:
            game_state = GAME_OVER
            game_over_time = pygame.time.get_ticks()

    elif game_state == GAME_OVER:
        screen.fill(BLACK)
        draw_background()
        game_over_text = large_font.render("Game Over", True, WHITE)
        score_display = font.render(f"Final Score: {player_score}", True, WHITE)
        restart_text = font.render("Click or Press R to Restart", True, WHITE)
        alpha = int(128 + 127 * np.sin(pygame.time.get_ticks() / 500))
        restart_text.set_alpha(alpha)
        screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 3))
        screen.blit(score_display, (WIDTH // 2 - score_display.get_width() // 2, HEIGHT // 2))
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 50))
        if mouse_clicked or keys[pygame.K_r]:
            game_state = PLAYING
            setup()

    pygame.display.flip()
    clock.tick(FPS)

# Запускаем игру
async def main():
    try:
        while True:
            await update_loop()
            await asyncio.sleep(1.0 / FPS)
    except:
        pygame.quit()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())