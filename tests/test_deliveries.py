from __future__ import annotations
import unittest
from unittest.mock import patch
from src.contexts.gameplay.application.game_manager import GameManager
from src.contexts.gameplay.domain.guard import Delivery, Guarda
from tests.support import TempHomeTestCase

class DeliveryTests(TempHomeTestCase):
    def test_delivery_creation_and_dict(self):
        d = Delivery("Ouro", 5, 500, "Servo1", 30.0)
        self.assertEqual(d.recurso, "Ouro")
        self.assertEqual(d.qtd, 5)
        self.assertEqual(d.status, "transito")
        
        data = d.to_dict()
        d2 = Delivery.from_dict(data)
        self.assertEqual(d2.recurso, "Ouro")
        self.assertEqual(d2.id, d.id)

    def test_game_manager_delivery_updates(self):
        game = GameManager()
        d = Delivery("Ouro", 2, 200, "Brutus", 10.0)
        game.entregas.append(d)
        
        # Simula passagem de tempo real
        game._update_deliveries(delta_real=5.0)
        self.assertEqual(d.timer, 5.0)
        self.assertEqual(d.status, "transito")
        
        game._update_deliveries(delta_real=6.0)
        self.assertEqual(d.status, "entregue")
        self.assertEqual(game.inventario["Ouro"], 2)

    def test_delivery_attack_simulation(self):
        game = GameManager()
        d = Delivery("Diamante", 1, 1000, "Mara", 60.0)
        game.entregas.append(d)
        
        # Força um ataque
        # _atk_check diminui com delta_real. 
        # Vamos avançar o tempo e forçar o check
        d._atk_check = 0.1
        
        # Fornece valores suficientes para o loop e o check de ataque
        with patch("random.random", side_effect=[0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]), \
             patch("src.contexts.gameplay.application.game_manager.GameManager._calcular_ataque_chance", return_value=1.0), \
             patch("src.contexts.gameplay.application.game_manager.GameManager._calcular_recuperacao", return_value=0.0):
            
            game._update_deliveries(delta_real=0.2)
            # Se o ataque ocorreu e não houve recuperação, o status muda para perdido
            self.assertEqual(d.status, "perdido")
            self.assertEqual(game.inventario["Diamante"], 0)

if __name__ == "__main__":
    unittest.main()
