import argparse
import secrets
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a secure bearer token.")
    parser.add_argument(
        "-l", "--length",
        type=int,
        default=32,
        help="Random bytes before URL-safe base64 encoding (default: 32).",
    )
    args = parser.parse_args()

    if args.length < 16:
        print("Error: length must be at least 16.", file=sys.stderr)
        sys.exit(1)

    print(secrets.token_urlsafe(args.length))


if __name__ == "__main__":
    main()
