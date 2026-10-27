# -*- coding: utf-8 -*-
"""Testes para o calculador de ração."""

import pytest
from racao import (
    NecessidadesCategorias,
    calcular_necessidades,
    _avaliar_combo,
    _avaliar_status,
)


class TestNecessidades:
    """Testa cálculo de necessidades por categoria."""

    def test_lactacao_sem_producao(self):
        """Vaca em lactação com 0L deve calcular necessidade base."""
        nec = calcular_necessidades("Lactação", 500, 0)
        assert nec["ms_kg"] > 0
        assert nec["pb_g"] > 0
        assert nec["energia_mcal"] > 0

    def test_lactacao_com_producao(self):
        """Vaca em lactação com 20L deve ter necessidade maior que base."""
        nec_base = calcular_necessidades("Lactação", 500, 0)
        nec_20l = calcular_necessidades("Lactação", 500, 20)

        # Com produção deve ser mais
        assert nec_20l["ms_kg"] > nec_base["ms_kg"]
        assert nec_20l["pb_g"] > nec_base["pb_g"]
        assert nec_20l["energia_mcal"] > nec_base["energia_mcal"]

    def test_seca(self):
        """Vaca seca deve ter menor necessidade."""
        nec_lac = calcular_necessidades("Lactação", 500, 0)
        nec_seca = calcular_necessidades("Seca", 500, 0)

        assert nec_seca["ms_kg"] < nec_lac["ms_kg"]
        assert nec_seca["pb_g"] < nec_lac["pb_g"]
        assert nec_seca["energia_mcal"] < nec_lac["energia_mcal"]

    def test_novilha(self):
        """Novilha deve ter necessidades intermediárias."""
        nec_nov = calcular_necessidades("Novilha", 400, 0)
        assert nec_nov["ms_kg"] > 0
        assert nec_nov["pb_g"] > 0

    def test_bezerro(self):
        """Bezerro deve ter alta concentração de proteína."""
        nec_bez = calcular_necessidades("Bezerro", 150, 0)
        # pb_g em gramas / ms_kg em kg → (pb_g / (ms_kg * 1000)) * 100 = pb_g / (ms_kg * 10)
        pb_pct_ms = nec_bez["pb_g"] / (nec_bez["ms_kg"] * 10)
        assert pb_pct_ms >= 15  # Alta proteína para crescimento

    def test_categoria_invalida(self):
        """Categoria inválida deve lançar erro."""
        with pytest.raises(ValueError):
            calcular_necessidades("Inválida", 500, 0)

    def test_peso_zero(self):
        """Peso zero deve resultar em necessidade zero."""
        nec = calcular_necessidades("Lactação", 0, 0)
        assert nec["ms_kg"] == 0
        assert nec["pb_g"] == 0

    def test_exemplo_vaca_500kg_20l(self):
        """Teste com exemplo da tarefa: vaca 500kg em lactação com 20L."""
        nec = calcular_necessidades("Lactação", 500, 20)

        # Resultado esperado aproximado:
        # Base: 500 × 4.5% = 22.5 kg MS
        # Extra lactação: 20 × 0.6 = 12 kg MS
        # Total: ~34.5 kg MS
        assert 30 < nec["ms_kg"] < 40, f"Esperado ~34.5, obteve {nec['ms_kg']}"

        # PB esperada: 22.5 × 15% × 10 + 20 × 100 = 3375 + 2000 = 5375g
        assert 4500 < nec["pb_g"] < 6000, f"Esperado ~5375g, obteve {nec['pb_g']}"


class TestStatus:
    """Testa avaliação de status (ok/aviso/ruim)."""

    def test_status_ok(self):
        """90% de atendimento deve ser OK."""
        status = _avaliar_status(90, 100)
        assert status == "ok"

    def test_status_aviso(self):
        """75% de atendimento deve ser aviso."""
        status = _avaliar_status(75, 100)
        assert status == "aviso"

    def test_status_ruim(self):
        """50% de atendimento deve ser ruim."""
        status = _avaliar_status(50, 100)
        assert status == "ruim"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
