import PyInstaller.__main__
import os
import shutil

def build():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, 'src')
    dist_dir = os.path.join(base_dir, 'dist')
    
    # Define assets to include
    # Format: (source_path, dest_folder_in_dist)
    # PyInstaller convention: "src;dest" for Windows
    add_data = [
        ('src/i18n/*.json', 'src/i18n'),
        ('data/config/company_logo', 'data/config/company_logo'),
        ('template/*.xlsm', 'template'),
        ('template/*.xlsx', 'template'),
    ]
    
    # Manual wildcard expansion
    import glob
    add_data_args = []
    
    for src_pattern, dst_folder in add_data:
        # Resolve source pattern to list of files
        abs_pattern = os.path.join(base_dir, src_pattern.replace('/', os.sep))
        files = glob.glob(abs_pattern)
        
        if not files:
            print(f"WARNING: No files found for pattern: {abs_pattern}")
            continue
            
        for f in files:
            # Skip temporary Office files
            if os.path.basename(f).startswith('~$'):
                continue
                
            # For each file, add it to the destination folder
            # PyInstaller format: "src;dest_folder"
            # We want the file to end up in 'dst_folder'
            arg = f'{f}{os.pathsep}{dst_folder}'
            add_data_args.append('--add-data')
            add_data_args.append(arg)

    # PyInstaller arguments
    args = [
        os.path.join(src_dir, 'main.py'),  # Entry point
        '--name=UllageMaster',
        '--noconsole',
        '--onefile',            # Single EXE output (all dependencies bundled)
        '--clean',
        '--noconfirm',
        f'--paths={src_dir}',   # Add src to module search path
        # Hidden imports usually needed for pandas/openpyxl/pyqt
        '--hidden-import=PyQt6',
        '--hidden-import=openpyxl',
        '--hidden-import=reportlab',
        '--hidden-import=ui',
        '--hidden-import=ui.main_window',
        '--hidden-import=ui.styles',
        '--hidden-import=ui.splash_screen',
        '--hidden-import=ui.widgets',
        '--hidden-import=models',
        '--hidden-import=core',
        '--hidden-import=export',
        '--hidden-import=reporting',
        '--hidden-import=utils',
    ] + add_data_args
    
    print("Running PyInstaller with args:", args)
    PyInstaller.__main__.run(args)
    
    # Post-build steps
    print("Performing post-build steps...")
    
    exe_dir = os.path.join(dist_dir, 'UllageMaster')
    
    # 1. Create empty directories
    for d in ['VOYAGES', 'REPORTS', 'backup']:
        path = os.path.join(exe_dir, d)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created directory: {d}")

    # 2. Ensure config file exists or is copied
    # We included data/config folder via add-data, but that puts it INSIDE the internal _internal folder usually (for onedir?)
    # Wait, --add-data with --onedir puts it in the INTERNAL folder? 
    # Actually, for --onedir, we might want config to be external/editable.
    
    # Let's copy 'data' folder to the root of EXE dir for editable config
    src_data = os.path.join(base_dir, 'data')
    dst_data = os.path.join(exe_dir, 'data')
    
    # If we want editable config, we should copy it manually and NOT bundle it inside the executable 
    # (or bundle a default and copy if missing).
    # Since the app usually looks for ./data relative to CWD or __file__.
    # Note: `src/utils/helpers.py` or similar probably determines paths.
    
    if os.path.exists(src_data):
        if os.path.exists(dst_data):
             # Remove existing to ensure fresh copy
             shutil.rmtree(dst_data)
        shutil.copytree(src_data, dst_data)
        print("Copied external data folder (for editable config)")

    # 3. Copy templates externally too if we want them editable without digging into _internal
    src_tpl = os.path.join(base_dir, 'template')
    dst_tpl = os.path.join(exe_dir, 'template')
    if os.path.exists(src_tpl):
        if os.path.exists(dst_tpl):
            shutil.rmtree(dst_tpl)
        shutil.copytree(src_tpl, dst_tpl)
        print("Copied external template folder")

    print(f"Build complete. Output in: {exe_dir}")

if __name__ == "__main__":
    build()
