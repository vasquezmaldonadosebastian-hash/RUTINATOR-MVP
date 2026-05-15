"""
Tests unitarios para domain/rules.py
Valida cálculos fisiológicos y lógica ATR pura.
"""
import pytest

from src.domain.rules import (
    calcular_imc,
    calcular_macros,
    calcular_gasto,
    estimar_grasa,
    estimar_agua,
    obtener_bloque_desde_semana,
    obtener_config_semana,
    obtener_split,
    obtener_patrones_sesion,
    es_semana_deload,
    generar_estrategia_nutricional,
    obtener_titulo_semana,
    obtener_mes_desde_semana,
)
from src.domain.models import BloqueATR, Macros


class TestCalculosFisiologicos:
    """Tests para funciones de cálculo fisiológico."""
    
    def test_calcular_imc_normal(self):
        """IMC normal para peso y altura típicos."""
        assert calcular_imc(70, 170) == pytest.approx(24.2, rel=0.1)
    
    def test_calcular_imc_obeso(self):
        """IMC alto para obesidad."""
        assert calcular_imc(100, 170) == pytest.approx(34.6, rel=0.1)
    
    def test_calcular_imc_cero(self):
        """IMC con valores cero retorna 0."""
        assert calcular_imc(0, 170) == 0.0
        assert calcular_imc(70, 0) == 0.0
    
    def test_estimar_grasa_masculino(self):
        """Estimación de grasa para masculino."""
        grasa = estimar_grasa(30, "Masculino", 25.0)
        assert 15 <= grasa <= 30
    
    def test_estimar_grasa_femenino(self):
        """Estimación de grasa para femenino."""
        grasa = estimar_grasa(30, "Femenino", 25.0)
        assert 20 <= grasa <= 35
    
    def test_estimar_agua(self):
        """Estimación de agua corporal."""
        agua = estimar_agua(20.0)
        assert agua == pytest.approx(40.0, rel=0.1)
    
    def test_calcular_macros_quemar_grasa(self):
        """Macros para quema de grasa."""
        macros = calcular_macros("Quemar Grasa", 70)
        
        assert isinstance(macros, Macros)
        assert macros.prot_g == 154  # 70 * 2.2
        assert macros.carb_g == 140  # 70 * 2.0
        assert macros.gras_g == 63   # 70 * 0.9
        assert macros.prot_p == 35
        assert macros.carb_p == 40
        assert macros.gras_p == 25
    
    def test_calcular_macros_ganar_musculo(self):
        """Macros para ganar músculo."""
        macros = calcular_macros("Ganar Músculo", 70)
        
        assert macros.prot_g == 140  # 70 * 2.0
        assert macros.carb_g == 245  # 70 * 3.5
        assert macros.gras_g == 70   # 70 * 1.0
    
    def test_calcular_macros_recomposicion(self):
        """Macros para recomposición."""
        macros = calcular_macros("Recomposición Corporal", 70)
        
        assert macros.prot_g == 147  # 70 * 2.1
        assert macros.carb_g == 175  # 70 * 2.5
        assert macros.gras_g == 70   # 70 * 1.0
    
    def test_calcular_gasto_principiante(self):
        """Gasto energético para principiante."""
        gasto = calcular_gasto("Principiante")
        
        assert gasto.tmb == 65
        assert gasto.neat == 18
        assert gasto.ejercicio == 8
        assert gasto.tef == 9
    
    def test_calcular_gasto_intermedio(self):
        """Gasto energético para intermedio."""
        gasto = calcular_gasto("Intermedio")
        
        assert gasto.tmb == 60
        assert gasto.neat == 20
    
    def test_calcular_gasto_avanzado(self):
        """Gasto energético para avanzado."""
        gasto = calcular_gasto("Avanzado")
        
        assert gasto.tmb == 55
        assert gasto.neat == 22


class TestATRPure:
    """Tests para lógica ATR pura."""
    
    @pytest.mark.parametrize("semana, esperado", [
        (1, BloqueATR.ACUMULACION),
        (2, BloqueATR.ACUMULACION),
        (4, BloqueATR.ACUMULACION),
        (5, BloqueATR.TRANSMUTACION),
        (6, BloqueATR.TRANSMUTACION),
        (8, BloqueATR.TRANSMUTACION),
        (9, BloqueATR.REALIZACION),
        (12, BloqueATR.REALIZACION),
    ])
    def test_obtener_bloque_desde_semana(self, semana, esperado):
        """Mapeo correcto de semana a bloque ATR."""
        assert obtener_bloque_desde_semana(semana) == esperado
    
    @pytest.mark.parametrize("semana", [4, 8, 12])
    def test_es_semana_deload(self, semana):
        """Semanas de deload correctas."""
        assert es_semana_deload(semana) is True
    
    @pytest.mark.parametrize("semana", [1, 2, 3, 5, 6, 7, 9, 10, 11])
    def test_no_es_semana_deload(self, semana):
        """Semanas que no son deload."""
        assert es_semana_deload(semana) is False
    
    def test_obtener_config_semana_acumulacion(self):
        """Config para semana de acumulación."""
        config = obtener_config_semana(2)
        
        assert config.bloque == BloqueATR.ACUMULACION
        assert config.rir == "RIR 3"
        assert config.series_base == 4
        assert config.reps == "10-12"
        assert config.es_deload is False
    
    def test_obtener_config_semana_transmutacion(self):
        """Config para semana de transmutación."""
        config = obtener_config_semana(6)
        
        assert config.bloque == BloqueATR.TRANSMUTACION
        assert config.rir == "RIR 2"
        assert config.series_base == 3
    
    def test_obtener_config_deload(self):
        """Config para semana de deload."""
        config = obtener_config_semana(4)
        
        assert config.es_deload is True
        assert config.rir == "RIR 4 (DELOAD)"
        assert config.reps == "12-15"
        assert config.series_base == 2  # 4 * 0.7 = 2.8 -> 2
    
    def test_obtener_split_2_dias(self):
        """Split para 2 días."""
        split = obtener_split(2)
        assert split == ["Full Body A", "Full Body B"]
    
    def test_obtener_split_3_dias(self):
        """Split para 3 días."""
        split = obtener_split(3)
        assert len(split) == 3
    
    def test_obtener_split_4_dias(self):
        """Split para 4 días."""
        split = obtener_split(4)
        assert split == ["Torso", "Pierna", "Torso", "Pierna"]
    
    def test_obtener_split_5_dias(self):
        """Split para 5 días."""
        split = obtener_split(5)
        assert len(split) == 5
    
    def test_obtener_patrones_full_body_a(self):
        """Patrones para Full Body A."""
        patrones = obtener_patrones_sesion("Full Body A")
        
        assert "Sentadilla" in patrones
        assert "Empuje_Horizontal" in patrones
        assert "Tracción_Horizontal" in patrones
        assert "Core" in patrones
    
    def test_obtener_patrones_torso(self):
        """Patrones para sesión Torso."""
        patrones = obtener_patrones_sesion("Torso")
        
        assert "Empuje_Horizontal" in patrones
        assert "Empuje_Vertical" in patrones
        assert "Tracción_Horizontal" in patrones
    
    def test_obtener_titulo_semana(self):
        """Etiquetas de semana correctas."""
        assert "Semana 1" in obtener_titulo_semana(1)
        assert "Acumulación" in obtener_titulo_semana(1)
        assert "DELOAD" in obtener_titulo_semana(4)
        assert "Transmutación" in obtener_titulo_semana(6)
        assert "Realización" in obtener_titulo_semana(10)
    
    def test_obtener_mes_desde_semana(self):
        """Conversión semana a mes."""
        assert obtener_mes_desde_semana(1) == 1
        assert obtener_mes_desde_semana(4) == 1
        assert obtener_mes_desde_semana(5) == 2
        assert obtener_mes_desde_semana(8) == 2
        assert obtener_mes_desde_semana(9) == 3
        assert obtener_mes_desde_semana(12) == 3


class TestNutricion:
    """Tests para generación de estrategias nutricionales."""
    
    def test_generar_estrategia_quemar_grasa(self):
        """Estrategia para quema de grasa."""
        macros = Macros(prot_g=154, carb_g=140, gras_g=63, prot_p=35, carb_p=40, gras_p=25)
        plan = generar_estrategia_nutricional("Quemar Grasa", macros)
        
        assert "déficit" in plan.estrategia_principal.lower()
        assert len(plan.guia_compras) > 0
        assert len(plan.reglas_oro) > 0
    
    def test_generar_estrategia_ganar_musculo(self):
        """Estrategia para ganar músculo."""
        macros = Macros(prot_g=140, carb_g=245, gras_g=70, prot_p=30, carb_p=45, gras_p=25)
        plan = generar_estrategia_nutricional("Ganar Músculo", macros)
        
        assert "superáv" in plan.estrategia_principal.lower()
    
    def test_generar_intro_neat(self):
        """Introducción NEAT personalizada."""
        from src.domain.rules import generar_intro_neat
        intro = generar_intro_neat("Quemar Grasa")

        assert "NEAT" in intro
        assert "quemar grasa" in intro.lower()

    def test_generar_estrategias_neat(self):
        """Estrategias NEAT."""
        from src.domain.rules import generar_estrategias_neat
        estrategias = generar_estrategias_neat()

        assert len(estrategias) == 5
        assert any("Caminata" in e for e in estrategias)
        assert any("Escaleras" in e for e in estrategias)