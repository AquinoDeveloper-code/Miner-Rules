import threading
import queue
import time
from typing import Any, Callable, Tuple, Optional

class DBWorker(threading.Thread):
    """
    Worker em segundo plano para processar operações de banco de dados
    sem travar a thread principal do Pygame.
    """
    def __init__(self, storage):
        super().__init__(name="DatabaseWorker", daemon=True)
        self.storage = storage
        self._queue = queue.Queue()
        self._running = True
        self.start()

    def run(self):
        while self._running:
            try:
                # Formato da task: (action_name, args_list, callback_func)
                task = self._queue.get(timeout=1.0)
                if task is None: 
                    break
                
                action, args, callback = task
                result = None
                
                try:
                    if action == "save":
                        # args: (player_id, data, total_money, play_time)
                        result = self.storage.save_game_state(*args)
                    elif action == "ranking":
                        # args: (limit,)
                        result = self.storage.get_top_rankings(*args)
                    elif action == "login":
                        # args: (username, password)
                        result = self.storage.login(*args)
                    elif action == "register":
                        # args: (username, password)
                        result = self.storage.register(*args)
                    elif action == "load":
                        # args: (player_id,)
                        result = self.storage.load_game_state(*args)
                except Exception as db_ex:
                    print(f"[DBWorker] Erro na operação '{action}': {db_ex}")
                    result = None
                
                if callback:
                    try:
                        callback(result)
                    except Exception as cb_ex:
                        print(f"[DBWorker] Erro no callback de '{action}': {cb_ex}")
                
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[DBWorker] Erro crítico no loop: {e}")

    def add_task(self, action: str, args: Tuple, callback: Optional[Callable] = None):
        """Adiciona uma tarefa para a fila de execução em segundo plano."""
        self._queue.put((action, args, callback))

    def stop(self):
        """Sinaliza para a thread parar."""
        self._running = False
        self._queue.put(None)
