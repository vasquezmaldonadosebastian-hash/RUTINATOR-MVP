"""
Tests unitarios para application/services.
Valida la orquestación de servicios y generación de programas.
"""
import pytest

from src.application.nutrition_service import NutritionService
from src.application.periodization_service import PeriodizationService
from src.application.training_generator_service import (
    AthleteData,
    TrainingGeneratorService,
)
from src.domain.models import BloqueATR, Macros, NutricionPlan, SemanaEntrenamiento


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def datos_atleta_base() -> AthleteData:
    """Datos de atleta para tests."""
    return AthleteData(
        nombre="Test Atleta",
        objetivo="Quemar Grasa",
        nivel="Principiante",
        edad=30,
        sexo="Masculino",
        peso=80.0,
        talla=175.0,
        equipamiento="Gimnasio completo",
        dias_semana=3,
        lesiones="Ninguna",
    )


@pytest.fixture
def datos_dict_base() -> dict:
    """Datos en formato dict (compatibilidad bot)."""
    return {
        "atleta": "Test Atleta",
        "objetivo": "Quemar Grasa",
        "nivel": "Principiante",
        "edad": 30,
        "sexo": "Masculino",
        "peso": 80.0,
        "talla": 175.0,
        "equipamiento": "Gimnasio completo",
        "dias_semana": "3",
        "lesiones": "Ninguna",
    }


# ─────────────────────────────────────────────
# NUTRITION SERVICE
# ─────────────────────────────────────────────

class TestNutritionService:
    """Tests para NutritionService."""

    def setup_method(self):
        self.service = NutritionService()

    def test_calcular_macros_quemar_grasa(self):
        macros = self.service.calcular_macros("Quemar Grasa", 80)
        assert isinstance(macros, Macros)
        assert macros.prot_g == 176   # 80 * 2.2
        assert macros.prot_p == 35

    def test_calcular_macros_ganar_musculo(self):
        macros = self.service.calcular_macros("Ganar Músculo", 80)
        assert macros.carb_g == 280   # 80 * 3.5
        assert macros.carb_p == 45

    def test_generar_plan_nutricional_retorna_plan(self):
        plan = self.service.generar_plan_nutricional("Quemar Grasa", 80)
        assert isinstance(plan, NutricionPlan)
        assert len(plan.estrategia_principal) > 0
        assert len(plan.guia_compras) > 0
        assert len(plan.reglas_oro) == 5

    def test_generar_info_neat(self):
        intro, estrategias = self.service.generar_info_neat("Quemar Grasa")
        assert "NEAT" in intro
        assert len(estrategias) == 5


# ─────────────────────────────────────────────
# PERIODIZATION SERVICE
# ─────────────────────────────────────────────

class TestPeriodizationService:
    """Tests para PeriodizationService."""

    def setup_method(self):
        self.service = PeriodizationService()

    def test_generar_programa_12_semanas(self, datos_atleta_base):
        semanas = self.service.generar_programa(
            nivel=datos_atleta_base.nivel,
            objetivo=datos_atleta_base.objetivo,
            lesiones=datos_atleta_base.lesiones,
            equipamiento=datos_atleta_base.equipamiento,
            dias_semana=datos_atleta_base.dias_semana,
        )
        assert len(semanas) == 12
        assert all(isinstance(s, SemanaEntrenamiento) for s in semanas)

    def test_generar_programa_semana_especifica(self, datos_atleta_base):
        semanas = self.service.generar_programa(
            nivel=datos_atleta_base.nivel,
            objetivo=datos_atleta_base.objetivo,
            lesiones=datos_atleta_base.lesiones,
            equipamiento=datos_atleta_base.equipamiento,
            dias_semana=datos_atleta_base.dias_semana,
            semana=5,
        )
        assert len(semanas) == 1
        assert semanas[0].numero == 5
        assert semanas[0].bloque == BloqueATR.TRANSMUTACION

    def test_semanas_deload_marcadas(self, datos_atleta_base):
        semanas = self.service.generar_programa(
            nivel=datos_atleta_base.nivel,
            objetivo=datos_atleta_base.objetivo,
            lesiones=datos_atleta_base.lesiones,
            equipamiento=datos_atleta_base.equipamiento,
            dias_semana=datos_atleta_base.dias_semana,
        )
        deloads = [s for s in semanas if s.es_deload]
        assert len(deloads) == 3
        assert {s.numero for s in deloads} == {4, 8, 12}

    def test_sesiones_por_dia(self, datos_atleta_base):
        semanas = self.service.generar_programa(
            nivel=datos_atleta_base.nivel,
            objetivo=datos_atleta_base.objetivo,
            lesiones=datos_atleta_base.lesiones,
            equipamiento=datos_atleta_base.equipamiento,
            dias_semana=3,
            semana=1,
        )
        assert len(semanas[0].sesiones) == 3

    def test_ejercicios_en_sesion(self, datos_atleta_base):
        semanas = self.service.generar_programa(
            nivel=datos_atleta_base.nivel,
            objetivo=datos_atleta_base.objetivo,
            lesiones=datos_atleta_base.lesiones,
            equipamiento=datos_atleta_base.equipamiento,
            dias_semana=3,
            semana=1,
        )
        primera_sesion = semanas[0].sesiones[0]
        assert len(primera_sesion.ejercicios) > 0
        # Cada ejercicio tiene series_reps y carga
        for ej in primera_sesion.ejercicios:
            assert ej.series_reps != ""
            assert ej.carga != ""

    @pytest.mark.parametrize("dias", [2, 3, 4, 5])
    def test_splits_por_dias(self, datos_atleta_base, dias):
        semanas = self.service.generar_programa(
            nivel=datos_atleta_base.nivel,
            objetivo=datos_atleta_base.objetivo,
            lesiones=datos_atleta_base.lesiones,
            equipamiento=datos_atleta_base.equipamiento,
            dias_semana=dias,
            semana=1,
        )
        assert len(semanas[0].sesiones) == dias


# ─────────────────────────────────────────────
# TRAINING GENERATOR SERVICE
# ─────────────────────────────────────────────

class TestTrainingGeneratorService:
    """Tests para TrainingGeneratorService."""

    def setup_method(self):
        self.service = TrainingGeneratorService()

    def test_generar_programa_completo(self, datos_atleta_base):
        programa = self.service.generar_programa_completo(datos_atleta_base)

        assert programa.athlete.nombre == "Test Atleta"
        assert programa.biometria.imc > 0
        assert programa.macros.prot_g > 0
        assert programa.gasto.tmb > 0
        assert len(programa.semanas) == 12
        assert programa.nutricion is not None

    def test_generar_programa_desde_dict(self, datos_dict_base):
        programa = self.service.generar_programa_desde_dict(datos_dict_base)

        assert programa.athlete.nombre == "Test Atleta"
        assert len(programa.semanas) == 12

    def test_generar_programa_semana_especifica(self, datos_dict_base):
        datos_dict_base["semana_actual"] = 3
        programa = self.service.generar_programa_desde_dict(datos_dict_base)

        assert len(programa.semanas) == 1
        assert programa.semanas[0].numero == 3

    def test_biometria_calculada(self, datos_atleta_base):
        programa = self.service.generar_programa_completo(datos_atleta_base)
        bio = programa.biometria

        # IMC para 80kg / 1.75m = 26.1
        assert bio.imc == pytest.approx(26.1, rel=0.05)
        assert bio.masa_muscular > 0
        assert bio.agua > 0

    def test_objetivo_quemar_grasa_macros(self, datos_atleta_base):
        programa = self.service.generar_programa_completo(datos_atleta_base)
        # Para quemar grasa: proteína alta
        assert programa.macros.prot_p == 35

    def test_objetivo_ganar_musculo_macros(self):
        datos = AthleteData(
            nombre="Test",
            objetivo="Ganar Músculo",
            nivel="Intermedio",
            edad=25,
            sexo="Masculino",
            peso=75.0,
            talla=180.0,
            equipamiento="Gimnasio completo",
            dias_semana=4,
        )
        programa = self.service.generar_programa_completo(datos)
        # Para ganar músculo: carbos altos
        assert programa.macros.carb_p == 45

    def test_filtro_lesion_rodilla(self):
        datos = AthleteData(
            nombre="Test",
            objetivo="Quemar Grasa",
            nivel="Principiante",
            edad=30,
            sexo="Femenino",
            peso=65.0,
            talla=165.0,
            equipamiento="Gimnasio completo",
            dias_semana=3,
            lesiones="rodilla derecha",
        )
        # No debe lanzar excepción — el filtro de lesiones debe aplicarse
        programa = self.service.generar_programa_completo(datos)
        assert len(programa.semanas) == 12

    def test_filtro_equipamiento_casa(self):
        datos = AthleteData(
            nombre="Test",
            objetivo="Recomposición Corporal",
            nivel="Principiante",
            edad=28,
            sexo="Masculino",
            peso=70.0,
            talla=172.0,
            equipamiento="Peso corporal",
            dias_semana=3,
        )
        programa = self.service.generar_programa_completo(datos)
        assert len(programa.semanas) == 12
