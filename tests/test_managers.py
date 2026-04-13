from __future__ import annotations
import unittest
from unittest.mock import patch
from src.contexts.gameplay.application.game_manager import GameManager
from src.contexts.gameplay.domain.manager import Gerente
from tests.support import TempHomeTestCase, make_servo

class ManagerTests(TempHomeTestCase):
    def test_manager_creation_and_autonomy(self):
        m = Gerente(tipo="junior")
        self.assertEqual(m.tipo, "junior")
        self.assertEqual(m.autonomia, "recomendacao")
        
        m.autonomia = "automatico"
        self.assertEqual(m.autonomia, "automatico")

    def test_manager_analysis_logic(self):
        m = Gerente(tipo="mestre")
        m.cfg_vender_idosos = True
        m.cfg_vender_idade_min = 50
        
        # Cria estado para análise
        servo_velho = make_servo(nome="Velho", idade=60, stamina=10)
        estado = {
            "escravos": [servo_velho],
            "ouro": 100,
            "loja": [],
            "guardas": [],
            "nivel_mina": 1
        }
        
        recs = m.analisar(estado)
        # Deve ter uma recomendação para vender o idoso
        venda_recs = [r for r in recs if r["tipo"] == "vender_idoso"]
        # Se não aparecer de primeira devido ao shuffle/subset, tentamos sem subset
        if not venda_recs:
            m.eficiencia = 1.0
            recs = m.analisar(estado)
            venda_recs = [r for r in recs if r["tipo"] == "vender_idoso"]
            
        self.assertTrue(len(venda_recs) > 0)
        self.assertEqual(venda_recs[0]["acao_tipo"], "vender_escravo")

    def test_game_manager_manager_execution(self):
        game = GameManager()
        # Adiciona um gerente com autonomia total e eficiência 1.0 para evitar shuffle
        m = Gerente(tipo="mestre")
        m.eficiencia = 1.0
        m.autonomia = "automatico"
        m.cfg_vender_idosos = True
        m.cfg_vender_idade_min = 30
        game.gerentes.append(m)
        
        # Adiciona um escravo que deve ser vendido
        e = make_servo(nome="VenderMe", idade=40, stamina=5)
        game.escravos.append(e)
        
        # Força o check do gerente
        # O intervalo do mestre é ~60s
        game._t_gerentes[m.id] = -100.0
        
        # Patch vender_escravo para verificar se foi chamado
        with patch.object(game, "vender_escravo") as mock_venda:
            game._update_gerentes(delta=1.0)
            mock_venda.assert_called()

if __name__ == "__main__":
    unittest.main()
