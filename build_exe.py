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
        ('src/i18n/*.json', 'i18n'),
        ('data/config/company_logo', 'data/config/company_logo'),
        ('template/*.xlsm', 'template'),
        ('template/*.xlsx', 'template'),
        ('assets/icon.ico', 'assets'),  # Include icon for runtime usage
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
        f'--icon={os.path.join(base_dir, "assets", "icon.ico")}', # EXE Icon
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
    
    # Create a nice release folder
    release_dir = os.path.join(dist_dir, 'UllageMaster_Release')
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    # Move EXE to release dir
    exe_file = os.path.join(dist_dir, 'UllageMaster.exe')
    if os.path.exists(exe_file):
        shutil.move(exe_file, os.path.join(release_dir, 'UllageMaster.exe'))
        print("Moved EXE to release directory")
    
    # 1. Create empty directories
    for d in ['VOYAGES', 'REPORTS', 'BACKUP']:
        path = os.path.join(release_dir, d)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created directory: {d}")

    # 2. Copy 'data' folder for external/editable config
    src_data = os.path.join(base_dir, 'data')
    dst_data = os.path.join(release_dir, 'data')
    
    if os.path.exists(src_data):
        shutil.copytree(src_data, dst_data)
        print("Copied external data folder")

    # 3. Copy templates externally
    src_tpl = os.path.join(base_dir, 'template')
    dst_tpl = os.path.join(release_dir, 'template')
    if os.path.exists(src_tpl):
        shutil.copytree(src_tpl, dst_tpl)
        print("Copied external template folder")

    print(f"Build complete. Release ready at: {release_dir}")

if __name__ == "__main__":
    build()
