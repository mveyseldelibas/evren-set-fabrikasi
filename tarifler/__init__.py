"""Tarif kaydı. SIRA, kuyruğa girecek tarif kimliklerini sırasıyla verir; her kimlik tarifler/<kimlik>.py modülüdür."""
import importlib

SIRA = ['sanayi_bolgesi', 'mezarlik', 'meyve_bahcesi_ve_bag', 'sulak_alan', 'zeytinlik', 'hobi_bahcesi', 'balik_ciftligi', 'liman_marina', 'futbol_sahasi', 'insaat_alani', 'universite_kampusu']


def yukle(tarif_id: str):
    return importlib.import_module(f"tarifler.{tarif_id}")
