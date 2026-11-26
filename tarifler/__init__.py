"""Tarif kaydı. SIRA, kuyruğa girecek tarif kimliklerini sırasıyla verir; her kimlik tarifler/<kimlik>.py modülüdür."""
import importlib

SIRA = ['sanayi_bolgesi', 'mezarlik', 'meyve_bahcesi_ve_bag', 'sulak_alan', 'zeytinlik', 'hobi_bahcesi', 'balik_ciftligi', 'liman_marina', 'futbol_sahasi', 'insaat_alani', 'universite_kampusu', 'sera', 'gunes_enerjisi', 'maden_ocagi', 'orman', 'tarim_arazisi', 'konut_alani', 'calilik_ve_funda', 'cayir_mera', 'ciplak_kaya_ve_kum', 'kentsel_park', 'ic_su_yuzeyleri', 'hayvancilik_tesisi', 'ticari_alan', 'cop_depolama', 'kumsal', 'atiksu_aritma', 'buyuk_otopark', 'saglik_egitim_yerleskesi', 'ulasim_enerji_altyapisi', 'arazi_ortusu_worldcover']


def yukle(tarif_id: str):
    return importlib.import_module(f"tarifler.{tarif_id}")
