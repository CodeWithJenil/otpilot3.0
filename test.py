import sys
import tty
import termios


def main():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)

        print("Press Return/Enter. Press Q to quit.")
        print("")

        while True:
            key = sys.stdin.read(1)

            print(
                f"Character: {key!r} | "
                f"ord: {ord(key)} | "
                f"hex: {ord(key):02x}"
            )

            if key.lower() == "q":
                break

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\nRestored terminal settings.")


if __name__ == "__main__":
    main()