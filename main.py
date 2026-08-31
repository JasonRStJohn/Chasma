from chasma.core.game import ChasmaGame
import arcade


def main():
    window = ChasmaGame()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
