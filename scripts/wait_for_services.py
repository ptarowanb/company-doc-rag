import argparse
import socket
import time


def wait_for(host: str, port: int, timeout_seconds: float) -> None:
    """TCP 포트가 열릴 때까지 제한 시간 동안 대기한다."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"{host}:{port}가 {timeout_seconds}초 안에 준비되지 않았습니다.")


def main() -> None:
    parser = argparse.ArgumentParser(description="TCP 서비스 준비 상태를 기다립니다.")
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    wait_for(args.host, args.port, args.timeout)


if __name__ == "__main__":
    main()

