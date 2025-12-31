"""
User Manual Content for UllageMaster.
Contains ASCII-formatted text for English and Turkish manuals.
"""

ASCII_HEADER = r"""
  _   _ _ _                   __  __           _
 | | | | | | __ _  __ _  ___|  \/  | __ _ ___| |_ ___ _ __
 | | | | | |/ _` |/ _` |/ _ \ |\/| |/ _` / __| __/ _ \ '__|
 | |_| | | | (_| | (_| |  __/ |  | | (_| \__ \ ||  __/ |
  \___/|_|_|\__,_|\__, |\___|_|  |_|\__,_|___/\__\___|_|
                  |___/
"""

MANUAL_EN = ASCII_HEADER + r"""
================================================================================
                               USER MANUAL
================================================================================

Welcome to UllageMaster, the professional calculator for Tanker Cargo Operations.

[ TABLE OF CONTENTS ]
1. Getting Started
2. Ship Configuration
3. Voyage Operations
4. Ullage Calculation (Grid)
5. Stowage Planning (Visual)
6. Reports & Export

--------------------------------------------------------------------------------
1. GETTING STARTED
--------------------------------------------------------------------------------
UllageMaster is designed to bridge the gap between shipboard ullage reports and 
stowage planning. It provides a unified interface for calculating cargo quantities 
based on ullage/soundings, trim, and temperature.

QUICK START:
1. Configure your ship (Settings -> Ship Configuration).
2. Create a new voyage (File -> New Voyage).
3. Enter cargo parcels (Ullage Table -> Edit Parcels).
4. Input ullage/temperature data in the grid.
5. Generate reports.

--------------------------------------------------------------------------------
2. SHIP CONFIGURATION
--------------------------------------------------------------------------------
Before starting, you must define your vessel's tank table.

WIZARD MODE:
Use the 'Ship Setup Wizard' to easily input data:
- Ship Name & VEF
- Tank Names & Capacities
- Ullage Tables (Paste from Excel supported)
- Trim Corrections
- Thermal Corrections

[TIP] You can copy-paste entire columns from Excel directly into the wizard grids.

--------------------------------------------------------------------------------
3. VOYAGE OPERATIONS
--------------------------------------------------------------------------------
- NEW VOYAGE (Ctrl+N): Clears current data.
- OPEN VOYAGE (Ctrl+O): Loads a saved .voyage file.
- SAVE VOYAGE (Ctrl+S): Saves current state including all readings and plans.

SEFER NOTLARI (Voyage Notes):
Add specific notes for the voyage via File -> Sefer Notlari.

--------------------------------------------------------------------------------
4. ULLAGE CALCULATION (Grid Interface)
--------------------------------------------------------------------------------
The 'Ullage Calculation' tab is the heart of the mathematical engine.

COLUMNS:
[Parcel]      Select cargo grade for the tank.
[Ullage]      Enter observed ullage (cm).
[Temp]        Enter observed temperature (°C).
[% Fill]      Auto-calculated. You can also ENTER % Fill to reverse-calc Ullage.
[Trim Corr]   Auto-looked up from Trim Table based on Fwd/Aft draft.
[VCF]         Volume Correction Factor (ASTM 54B).
[GSV]         Gross Standard Volume (m³ at 15°C).
[MT (Air)]    Commercial Weight (Metric Tons in Air).

[!] WARNING COLORS:
    YELLOW (High):    > 95% Fill
    RED (High High):  > 98% Fill (Critical Alert)

--------------------------------------------------------------------------------
5. STOWAGE PLANNING (Visual Interface)
--------------------------------------------------------------------------------
The 'Stowage Plan' tab provides a drag-and-drop interface for planning.

LAYOUT:
+-------------------------------------------------------------+
|  [ CARGO LEGEND ]        (Draggable Cargo Cards)            |
+-------------------------------------------------------------+
|                                                             |
|   [1P]    [2P]    [3P]    [4P]    [5P]    [6P]              |
|                                                             |
|           ( V I S U A L   S H I P   D E C K )               |
|                                                             |
|   [1S]    [2S]    [3S]    [4S]    [5S]    [6S]              |
|                                                             |
+-------------------------------------------------------------+
|  [CHARTERER ORDER]              [LOADING PLAN TABLE]        |
+-------------------------------------------------------------+

ACTIONS:
- DRAG cargo from Legend to a Tank to assign it.
- DRAG from Tank to Tank to move cargo.
- RIGHT-CLICK a tank to Edit or Empty it.
- 'Colorize' Button: Auto-color codes parcels by Receiver name.

--------------------------------------------------------------------------------
6. REPORTS & EXPORT
--------------------------------------------------------------------------------
Generate professional reports via the 'Report Functions' tab or Export Menu.

AVAILABLE EXPORTS:
- PDF Reports: Detailed ullage report with signature fields.
- Excel Export: Full data dump for further analysis.
- Stowage Plan PDF: Visual ship schematic and loading plan.
- ASCII Report: Text-based summary for telex/email.
- JSON: Raw data export for integration.

TEMPLATE REPORT:
Place a 'TEMPLATE.XLSM' in the application folder to use the 
'Template Report' feature, which auto-fills your company specific forms.

================================================================================
"""

MANUAL_TR = ASCII_HEADER + r"""
================================================================================
                            KULLANIM KILAVUZU
================================================================================

UllageMaster'a hoş geldiniz - Tanker Yük Operasyonları için profesyonel hesaplayıcı.

[ İÇİNDEKİLER ]
1. Başlarken
2. Gemi Konfigürasyonu
3. Sefer İşlemleri
4. Ullage Hesaplama (Tablo)
5. Yükleme Planı (Görsel)
6. Raporlar ve Dışa Aktarım

--------------------------------------------------------------------------------
1. BAŞLARKEN
--------------------------------------------------------------------------------
UllageMaster, gemi ullage raporları ile yükleme planlaması arasındaki boşluğu 
doldurmak için tasarlanmıştır. Ullage/iskandil, trim ve sıcaklık verilerine 
dayalı olarak yük miktarlarını hesaplamak için birleşik bir arayüz sunar.

HIZLI BAŞLANGIÇ:
1. Geminizi yapılandırın (Ayarlar -> Gemi Konfigürasyonu).
2. Yeni bir sefer oluşturun (Dosya -> Yeni Sefer).
3. Yük parsellerini tanımlayın (Ullage Tablosu -> Edit Parcels).
4. Tabloya ullage ve sıcaklık verilerini girin.
5. Raporlarınızı oluşturun.

--------------------------------------------------------------------------------
2. GEMİ KONFİGÜRASYONU
--------------------------------------------------------------------------------
Başlamadan önce geminizin tank tablolarını tanımlamanız gerekir.

SİHİRBAZ MODU (Wizard):
'Ship Setup Wizard' kullanarak verileri kolayca girebilirsiniz:
- Gemi Adı ve VEF
- Tank İsimleri ve Kapasiteleri
- Ullage Tabloları (Excel'den yapıştırma desteklenir)
- Trim Düzeltmeleri
- Termal Genleşme Faktörleri

[İPUCU] Excel'deki tüm sütunları kopyalayıp sihirbaz tablolarına yapıştırabilirsiniz.

--------------------------------------------------------------------------------
3. SEFER İŞLEMLERİ
--------------------------------------------------------------------------------
- YENİ SEFER (Ctrl+N): Mevcut verileri temizler.
- SEFERİ AÇ (Ctrl+O): Kaydedilmiş .voyage dosyasını yükler.
- SEFERİ KAYDET (Ctrl+S): Tüm okumaları ve planları içeren durumu kaydeder.

SEFER NOTLARI:
Sefere özel notlarınızı Dosya -> Sefer Notları menüsünden ekleyebilirsiniz.

--------------------------------------------------------------------------------
4. ULLAGE HESAPLAMA (Tablo Arayüzü)
--------------------------------------------------------------------------------
'Ullage Calculation' sekmesi, uygulamanın matematik motorudur.

SÜTUNLAR:
[Parcel]      Tank için yük cinsini seçin.
[Ullage]      Ölçülen ullage değerini girin (cm).
[Temp]        Ölçülen sıcaklığı girin (°C).
[% Fill]      Otomatik hesaplanır. Ayrıca % Doluluk girerek tersine hesaplama yapabilirsiniz.
[Trim Corr]   Baş/Kıç draftına göre Trim tablosundan otomatik alınır.
[VCF]         Hacim Düzeltme Faktörü (ASTM 54B).
[GSV]         Gross Standart Hacim (15°C'de m³).
[MT (Air)]    Ticari Ağırlık (Havada Metrik Ton).

[!] UYARI RENKLERİ:
    SARI (Yüksek):        > %95 Doluluk
    KIRMIZI (Çok Yüksek): > %98 Doluluk (Kritik Uyarı)

--------------------------------------------------------------------------------
5. YÜKLEME PLANI (Görsel Arayüz)
--------------------------------------------------------------------------------
'Stowage Plan' sekmesi, sürükle-bırak yöntemiyle planlama yapmanızı sağlar.

YERLEŞİM:
+-------------------------------------------------------------+
|  [ YÜK LEJANDI ]         (Sürüklenebilir Yük Kartları)      |
+-------------------------------------------------------------+
|                                                             |
|   [1P]    [2P]    [3P]    [4P]    [5P]    [6P]              |
|                                                             |
|           ( G E M İ   G Ü V E R T E   P L A N I )           |
|                                                             |
|   [1S]    [2S]    [3S]    [4S]    [5S]    [6S]              |
|                                                             |
+-------------------------------------------------------------+
|  [YÜKLEME TALEPLERİ]            [YÜKLEME PLANI TABLOSU]     |
+-------------------------------------------------------------+

İŞLEMLER:
- Yükü Lejanttan bir Tanka SÜRÜKLEYİN.
- Yükü bir Tanktan diğerine taşıyın.
- Düzenlemek veya Boşaltmak için bir tanka SAĞ TIKLAYIN.
- 'Colorize' Butonu: Parselleri Alıcı adına göre otomatik renklendirir.

--------------------------------------------------------------------------------
6. RAPORLAR VE DIŞA AKTARIM
--------------------------------------------------------------------------------
'Report Functions' sekmesi veya Export Menüsü üzerinden profesyonel raporlar oluşturun.

DIŞA AKTARIM SEÇENEKLERİ:
- PDF Raporları: İmza alanları içeren detaylı ullage raporu.
- Excel Export: Detaylı analiz için tam veri dökümü.
- Stowage Plan PDF: Görsel gemi şeması ve yükleme planı.
- ASCII Raporu: Telex/Email için metin tabanlı özet.
- JSON: Entegrasyon için ham veri.

ŞABLON RAPORU (Template Report):
Uygulama klasörüne 'TEMPLATE.XLSM' dosyasını koyarak, şirketinize özel 
formların otomatik doldurulmasını sağlayan "Template Report" özelliğini kullanabilirsiniz.

================================================================================
"""
