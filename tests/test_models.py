"""
Tests unitarios para domain/models.py
Valida modelos Pydantic.
"""
import pytest
from pydantic import ValidationError

from src.domain.models import (
    Athlete,
    Biometria,
    Macros,
    Nivel,
    Objetivo,
    Sexo,
    Equipamiento,
)


class TestAthlete:
    """Tests para el modelo Athlete."""
    
    def test_athlete_valido(self):
        """Athlete con datos válidos."""
        athlete = Athlete(
            nombre="Juan Pérez",
            objetivo=Objetivo.QUEMAR_GRASA,
            nivel=Nivel.INTERMEDIO,
            sexo=Sexo.MASCULINO,
            edad=30,
            peso=80.0,
            talla=175.0,
            equipamiento=Equipamiento.GIMNASIO_COMPLETO,
            dias_semana=4,
        )
        
        assert athlete.nombre == "Juan Pérez"
        assert athlete.edad == 30
    
    def test_athlete_validacion_edad(self):
        """Validación de edad fuera de rango."""
        with pytest.raises(ValidationError):
            Athlete(
                nombre="Test",
                objetivo=Objetivo.QUEMAR_GRASA,
                nivel=Nivel.PRINCIPIANTE,
                sexo=Sexo.MASCULINO,
                edad=5,  # Inválido
                peso=70,
                talla=170,
                equipamiento=Equipamiento.GIMNASIO_COMPLETO,
                dias_semana=3,
            )
    
    def test_athlete_validacion_peso(self):
        """Validación de peso fuera de rango."""
        with pytest.raises(ValidationError):
            Athlete(
                nombre="Test",
                objetivo=Objetivo.GANAR_MUSCULO,
                nivel=Nivel.PRINCIPIANTE,
                sexo=Sexo.FEMENINO,
                edad=25,
                peso=500,  # Inválido
                talla=165,
                equipamiento=Equipamiento.GIMNASIO_COMPLETO,
                dias_semana=3,
            )
    
    def test_athlete_normalizar_lesiones(self):
        """Normalización de lesiones vacías."""
        athlete = Athlete(
            nombre="Test",
            objetivo=Objetivo.RECOMPOSICION,
            nivel=Nivel.AVANZADO,
            sexo=Sexo.MASCULINO,
            edad=35,
            peso=75,
            talla=180,
            equipamiento=Equipamiento.GIMNASIO_COMPLETO,
            dias_semana=5,
            lesiones="ninguna",
        )
        
        assert athlete.lesiones == "Ninguna"
    
    def test_athlete_dias_semana(self):
        """Validación de días por semana."""
        with pytest.raises(ValidationError):
            Athlete(
                nombre="Test",
                objetivo=Objetivo.QUEMAR_GRASA,
                nivel=Nivel.PRINCIPIANTE,
                sexo=Sexo.MASCULINO,
                edad=25,
                peso=70,
                talla=170,
                equipamiento=Equipamiento.GIMNASIO_COMPLETO,
                dias_semana=7,  # Inválido
            )


class TestBiometria:
    """Tests para Biometria."""
    
    def test_biometria(self):
        """Biometria con valores."""
        bio = Biometria(
            peso=70,
            talla=170,
            imc=24.2,
            masa_muscular=40,
            agua=40,
            grasa_visceral=10,
        )
        
        assert bio.peso == 70
        assert bio.imc == 24.2


class TestMacros:
    """Tests para Macros."""
    
    def test_macros(self):
        """Macros con valores."""
        macros = Macros(
            prot_g=150,
            carb_g=200,
            gras_g=60,
            prot_p=30,
            carb_p=40,
            gras_p=30,
        )
        
        assert macros.prot_g == 150
        assert macros.prot_p == 30