# UllageMaster — Tam Özellik Envanteri ve Web Parite Durumu

Masaüstü (PyQt6) uygulamasının kod incelemesinden çıkarılan eksiksiz özellik listesi.
Durum: ✅ webde var · ⚠️ webde kısmi · ❌ webde yok

---

## 1. Ana Pencere — 5 Sekme

| Sekme | İçerik | Web |
|---|---|---|
| 📂 Voyages | Sefer dosyası gezgini + önizleme | ⚠️ (basit liste var; not/özet/önizleme yok) |
| 📋 Stowage Plan | **Sürükle-bırak yükleme planlayıcısı** | ✅ (Faz A tamamlandı 2026-07-03: kargo tanımı, sürükle-bırak, 97.7 kuralları, takas, kilit/hariç, %97.7 + Colorize, plan görüntüleyici, çift yönlü aktarım, seferle kayıt) |
| 📊 Ullage Calculation | Excel benzeri hesap grid'i | ✅ (çekirdek tam; grid ekstraları eksik) |
| 📑 Report Functions | Resmi rapor üretimi (başlıklar, parcel seçimi) | ❌ |
| ⚖️ Discrepancy/Protests | Yükleme + tahliye ayrışım kartları, protesto | ✅ (Faz B tamamlandı 2026-07-03: 7 satırlı yükleme + 12 satırlı tahliye kartları, ‰ renk eşikleri, tek/çoklu Letter of Protest PDF, şirket logosu) |

---

## 2. STOWAGE PLANLAYICI (uygulamanın kalbi) — ❌ webde yok

### 2.1 Kargo tanımı (Charterer Order — `CargoInputWidget`)
- Tablo: Yük Tipi | Ton | Density (ton/m³) | Hacim (m³, otomatik = ton/density) | Alıcı(lar) | Düzenle
- Girişler: yük tipi, ton (0.01–1.000.000, 2 hane), density (0.01–10, 4 hane, varsayılan 0.8500), alıcı (virgülle çoklu)
- Doğrulama: tip boş olamaz, ton>0, density>0
- Düzenleme modali (aynı unique_id ve renk korunur)

### 2.2 Kargo lejantı (`CargoLegendWidget` — sürüklenebilir kartlar)
- Yatay kaydırmalı kart şeridi; her kart: yük tipi, alıcı, **kalan miktar rozeti**
  - kalan ≤ 0.5 m³ → yeşil "✓ Tamamlandı"
  - kalan > 0.5 → beyaz "X m³ kaldı"
  - kalan < −0.5 → amber "X m³ fazla"
- Kart arka planı = cargo.custom_color veya palet `[#FF6B6B, #4ECDC4, #45B7D1, #96CEB4, #FFEAA7, #DDA0DD, #F7DC6F, #BB8FCE, #85C1E9, #F8B500]` (index mod)
- Sağ tık → 🎨 Renk Değiştir (renk seçici)
- Sürükleme: MIME `application/x-cargo-id`, 3px eşik

### 2.3 Gemi şeması tank kartları (`DraggableTankCard`)
- Kart içeriği: kapasite (m³) → kargo rozeti (tip + alıcı, kontrast metin) → yüklü miktar → **doluluk progress bar** (kargo renginde, % etiketli)
- Boş tank: gri "Boş"
- **Planlama dışı** tank: kesikli kenarlık, gri, "⚠ Planlama Dışı" (drag-drop reddeder)
- **Kilitli** tank: turuncu "🔒 Kilitli" (drag-drop reddeder, toplu temizlikte korunur)

### 2.4 Sürükle-bırak kuralları
- **Kargo → Tank** (`handle_cargo_drop`):
  1. `MAX_FILL_FACTOR = 0.977` → `max_capacity = kapasite × 0.977`
  2. Tankta farklı kargo varsa önce temizlenir; aynı kargoysa üstüne eklenir (97.7 tavanlı)
  3. `kalan = cargo.quantity − toplam_yüklenen`
  4. `yüklenecek = min(boş_alan, kalan)` → `TankAssignment(tank_id, cargo, qty)`
- **Tank ↔ Tank takas** (`handle_tank_swap`): iki tankın kargoları yer değiştirir, her biri hedef tankın %97.7'siyle sınırlanır
- Tank sağ tık menüsü: Boşalt · 🔒 Kilitle/Kaldır · ⚠ Planlama Dışı Bırak/Dahil Et · 🎨 Renk Değiştir

### 2.5 Araç butonları
- **%97.7 butonu**: dolu tüm tankları %97.7'ye tamamlar (SLOP ve planlama-dışı hariç), onay diyaloğu
- **Colorize butonu** (basılı tut): parcelleri alıcı adının ilk 4 karakterine göre gruplar, parlak renk atar; bırakınca eski renkler döner

### 2.6 Plan görüntüleyici (Loading Plan — `PlanViewerWidget`)
- Tablo: Yük Tipi | Alıcı | İstenen (m³) | Yüklenen (m³) | Fark (m³) | Durum
- Durum: "✓ Tamamlandı" (yeşil, |fark|<0.01) · "Eksik %X" (sarı) · "Fazla %X" (kırmızı)
- Özet: Kapasite | Yüklenen | Oran % | Talep Karşılama %

### 2.7 Çift yönlü aktarım
- **Stowage → Ullage** (Ctrl+Shift+T, `_transfer_stowage_to_ullage`):
  - Her kargo → Parcel (id=1'den, name/receiver/density/renk kopyalanır)
  - Her atama → tank reading: parcel_id, density; SLOP değilse `temp=20.0`, `fill_percent=97.7` → ullage tersten hesaplanır
  - Ullage sekmesine geçer
- **Ullage → Stowage** (Ctrl+Shift+U, `_transfer_ullage_to_stowage`):
  - Parcel bazında GOV toplanır → StowageCargo(quantity=ΣGOV)
  - SLOP özel: cargo_type="SLOP", density=0.85, renk #9CA3AF
  - Her tank → TankAssignment(quantity_loaded=GOV)

### 2.8 Veri modeli (`stowage_plan.py`)
- `StowageCargo{unique_id, cargo_type, quantity(m³), receivers[], density, custom_color}`
- `TankAssignment{tank_id, cargo, quantity_loaded}`
- `StowagePlan{cargo_requests[], assignments{tank_id→}, excluded_tanks[], plan_name, id}`
- Sefer dosyasına gömülü kaydedilir (aşağıda §7)

---

## 3. Ullage Grid ekstraları

| Özellik | Detay | Web |
|---|---|---|
| 20 sütun | Tank, Parcel, Grade, Receiver, Tank No(alıcı), Ullage, Temp, %Fill, TrimCorr, CorrUllage, TOV, Therm, GOV, VCF, GSV, VACDens, MT(VAC), AirDens, MT(Air), Tank(tekrar) | ⚠️ (Grade/Receiver/TankNo ve sondaki tekrar sütunu yok) |
| Çoklu hücre seçimi + yaz-hepsine-uygula | Aynı sütunda 2+ hücre seç, karakter yaz → toplu giriş diyaloğu | ⚠️ (yalnızca "Set all" satırı var; seçimli toplu giriş yok) |
| Ctrl+C kopyalama | Seçili hücreler tab-ayrılmış panoya | ❌ |
| Seçim istatistikleri | Durum çubuğunda SELECTED TOTAL / AVERAGE | ❌ |
| Parcel sağ-tık menüsü | None/SLOP/parcel listesi/Edit Parcels... | ⚠️ (dropdown var, menü yok) |
| Parcel satır renklendirme | Tüm satır parcel renginde, kontrast metin | ⚠️ (yalnız sol şerit) |
| BL Date | Takvimli tarih seçici | ✅ |
| Zabit adları | Blur'da gemi konfigürasyonuna kaydedilir | ⚠️ (seferde tutuluyor, gemiye yazılmıyor) |
| SLOP parcel | ID "0", gri, toplam dışı | ✅ |

## 4. Ayrışım (Discrepancy) & Protesto

### 4.1 Yükleme kartı (7 satır) — ⚠️ webde kısmi
1. B/L Figure (giriş) · 2. Ship W/O VEF · 3. Fark W/O VEF · 4. **Fark W/O VEF ‰** · 5. Ship with VEF (=W/O VEF ÷ VEF) · 6. Fark with VEF · 7. **Fark with VEF ‰**
- ‰ renk eşikleri: |‰|≥3 kırmızı · 2≤|‰|<3 turuncu · <2 beyaz/yeşil

### 4.2 Tahliye kartı (12 satır) — ✅ webde var (Faz B)
1. B/L · 2. Ship Figure Loading Port (giriş) · 3. Ship Arrival · 4. Arrival with VEF · 5. **Transit Loss** (3−2) · 6. Arrival-BL ‰ W/O VEF · 7. Arrival-BL ‰ VEF · 8. **OUTTURN** (giriş) · 9. Outturn-BL fark · 10. Outturn-BL ‰ · 11. Outturn-Arrival fark · 12. Outturn-Arrival ‰
- Parcel alanları: `bl_loading, ship_figure_loading, outturn_figure` (modelde mevcut)

### 4.3 Letter of Protest PDF (CBO 082) — ✅ webde var (Faz B; `/export/protest?operation=&parcel_id=`)
- Şirket logosu + "INTEGRATED MANAGEMENT SYSTEM MANUAL Chapter 7.5" başlığı
- İngilizce + Türkçe yasal metin; kargo tablosu (Grade, B/L, B/L Date)
- Yükleme: 7 satırlık veri tablosu · Tahliye: 8 satırlık (outturn dahil)
- İmza blokları (Terminal Temsilcisi / Master), liman-terminal-tarih
- Tek parcel veya çoklu sayfa (`generate_multi`) — sağ tık "Protest" / "Protest All"

## 5. Report Functions sekmesi — ❌ webde yok
- Alanlar: Actual Port, Terminal, MMC No, Report Type, Product, Receiver, Draft (oto), Report Date, SLOP Label, Remarks
- **MRU otomatik tamamlama** (`report_history.ini`, alan başına 10 kayıt)
- Parcel seçim listesi (renkli, "ALL PARCELS")
- Butonlar: Total Ullage raporu · Selected Parcels raporu · Stowage Plan raporu

## 6. Export/Rapor türleri

| Tür | İçerik | Web |
|---|---|---|
| Excel (.xlsx) | Renk kodlu grid + toplamlar | ✅ (benzer) |
| Basit PDF | Tablo raporu | ✅ |
| Görsel Stowage PDF | Gemi gövdesi çizimi + tank hücreleri + parcel lejantı + draft kutusu | ⚠️ (şerit düzeni var; gövde çizimi/lejant %50 saydamlık farklı) |
| **Resmi Ullage Report PDF** (CBO 07, `pdf_engine.py`) | Logo, 13 sütunlu tablo (Free water dahil), özet tablosu, Remarks, imza blokları, "Controlled Copy" | ❌ |
| **Protest PDF** (CBO 082) | §4.3 | ❌ |
| ASCII (.txt) | 100 karakter sabit genişlik, [!!]/[!]/[L] uyarıları | ❌ |
| JSON | Sefer + tank + toplam yapısı | ❌ (API zaten JSON veriyor) |
| **XLSM Şablon** | Kullanıcının TEMPLATE.XLSM'ine DATA / DATA_PARCEL / DATA_VOYAGE sayfaları enjekte edilir, VBA korunur | ❌ |
| Şablon üretici/ayrıştırıcı | Gemi kalibrasyonu için 4 sayfalı Excel şablonu (INSTRUCTIONS, ULLAGE_TABLES, TRIM_CORRECTION, THERMAL_CORRECTION) üret + geri oku | ❌ |

## 7. Sefer dosyası ve gezgin
- `.voyage` = JSON `{version: "2.0", voyage: {...}, stowage_plan: {...}}` — stowage planı seferle birlikte kaydedilir
- Voyage Explorer: dosya listesi (çoklu seçim), **sefer notları** (düzenle+kaydet), **kargo özeti çipleri** (parcel renkli, MT Air), **salt-okunur stowage önizleme şeması**, çift tık yükle
- Splitter konumları `VoyageExplorer.ini`'de saklanır
- Web durumu: ⚠️ (liste + CRUD var; notlar alanı var ama gezgin önizlemeleri yok, stowage_plan alanı yok)

## 8. Kurulum ve yapılandırma
- **Gemi Kurulum Sihirbazı** (6 sayfa): gemi bilgisi (VEF, trim değerleri serbest liste, termal aç/kapa, slop density) → tank üretici (1–15 çift + 0–4 slop) → ullage grid'leri (Excel'den **Ctrl+V yapıştırma**, "ilkini hepsine kopyala") → trim grid'leri (dinamik trim sütunları) → termal → özet/doğrulama — ❌ webde yok (yalnız JSON import + CSV upload var)
- **Config Editor**: ad, VEF, kapasiteler, ullage/trim tabloları düzenlenebilir; trim değerleri ve termal durumu kilitli — ❌
- **Parola koruması**: ayarlar/single restore için `19771977` — ❌ (webde hesap sistemi var, gerek olmayabilir)
- **Yedekleme/Geri Yükleme**: ship_config.json + company_logo.png → ./BACKUP; parola onaylı geri yükleme — ❌ (webde DB volume)
- **Şirket logosu**: `data/config/company_logo/LOGO.PNG` → resmi PDF'lerde kullanılır — ✅ (Faz B: gemi başına logo yükleme, protest PDF'te kullanılıyor)

## 9. Genel platform özellikleri

| Özellik | Masaüstü | Web |
|---|---|---|
| Tema | Koyu (Slate paleti) — tek tema | Açık — tek tema ❌ geçiş yok |
| Dil | TR/EN JSON i18n (`t()` fonksiyonu), kılavuz iki dilli | ❌ (arayüz İngilizce) |
| Birimler | Metrik sabit (imperial PRD'de var, uygulanmamış) | aynı |
| Ondalık | Nokta/virgül her ikisi kabul (locale bağımsız) | ⚠️ (num() virgülü kabul ediyor) |
| Kısayollar | Ctrl+N/O/S/Shift+S, **Ctrl+E bağlama duyarlı temizle**, Ctrl+Shift+T/U aktarımlar, Ctrl+C, F1 kılavuz | ❌ |
| Kullanım kılavuzu (F1) | İki dilli ASCII kılavuz diyaloğu | ❌ |
| Undo | Yok (sefer dosyası = kayıt noktası) | aynı |
| Splash screen | Tank animasyonlu açılış | — (gerek yok) |

---

## Önerilen web fazları
1. **Faz A (kritik)**: Stowage planlayıcı — kargo tanımı, sürüklenebilir kartlar, tank kartları+progress, 97.7 kuralları, kilit/hariç, %97.7 & Colorize, plan görüntüleyici, çift yönlü aktarım, stowage'ın seferle kaydı
2. **Faz B**: Tahliye ayrışım kartı (12 satır) + Letter of Protest PDF (tek/çoklu) + şirket logosu yükleme
3. **Faz C**: Resmi Ullage Report PDF (CBO 07) + Report Functions (MRU, parcel seçimi, remarks)
4. **Faz D**: Voyage Explorer zenginleştirme (notlar, çipler, önizleme), grid ekstraları (çoklu seçim toplu giriş, kopyalama, seçim istatistikleri, satır renklendirme)
5. **Faz E**: i18n TR/EN, koyu tema, ASCII/XLSM exportlar, kurulum sihirbazı
