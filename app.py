import socket
from threading import Thread

from backend.api import criar_app
from backend.database import init_db
from frontend.interface import NfeSystem


API_HOST = "127.0.0.1"
API_PORT = 5000


def porta_em_uso(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0


def iniciar_api_em_segundo_plano():
    if porta_em_uso(API_HOST, API_PORT):
        return

    api = criar_app()
    thread = Thread(
        target=lambda: api.run(
            host=API_HOST,
            port=API_PORT,
            debug=False,
            use_reloader=False,
        ),
        daemon=True,
    )
    thread.start()


if __name__ == "__main__":
    init_db()
    iniciar_api_em_segundo_plano()
    app = NfeSystem()
    app.mainloop()
