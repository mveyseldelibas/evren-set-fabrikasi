"""Eğitim işi gövdesi ve maliyet kuralı."""
from __future__ import annotations

import copy

TAVAN_CR = 30.0        # bir eğitim için en çok bu kadar CR
KATSAYI = 2.4          # kuru koşu tahmini gerçek maliyetin altında kalıyor (ölçüm: 13,3 tahmin / 24,8 gerçek); güvenlik çarpanı

HIPER_TABAN = {
    "amp": True, "box": 7.5, "cls": 0.5, "dfl": 1.5, "lr0": 0.001, "lrf": 0.001, "rect": False, "seed": 0,
    "batch": 16, "cache": "disk", "hsv_h": 0.015, "hsv_s": 0.7, "hsv_v": 0.4, "mixup": 0.0, "scale": 0.5,
    "shear": 0, "cos_lr": True, "fliplr": 0.5, "flipud": 0.5, "freeze": 0, "mosaic": 1, "degrees": 0,
    "dropout": 0, "erasing": 0.4, "workers": 8, "fraction": 1, "momentum": 0.937, "patience": 25,
    "optimizer": "AdamW", "translate": 0.1, "copy_paste": 0, "single_cls": False, "val_period": 0,
    "multi_scale": False, "perspective": 0, "save_period": -1, "close_mosaic": 10, "target_steps": 3,
    "weight_decay": 0.001, "warmup_epochs": 3, "warmup_bias_lr": 0.1, "label_smoothing": 0, "warmup_momentum": 0.8,
}


def govde(tarif: dict, surum_id: str, epok: int) -> dict:
    hp = copy.deepcopy(HIPER_TABAN)
    hp.update(run_name=tarif["model_adi"], epochs=epok, imgsz=tarif["imgsz"], task=tarif["gorev"],
              tags=[tarif["model_adi"], tarif["mimari"], "sentinel2", "turkiye"])
    return {"dataset_version_id": surum_id, "architecture": tarif["mimari"], "hyperparams": hp}


def maliyet_uygun(tahmin_cr: float) -> bool:
    return tahmin_cr * KATSAYI <= TAVAN_CR
