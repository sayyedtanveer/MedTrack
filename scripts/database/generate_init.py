import os
import glob

models_dir = r'c:\Users\sayye\source\repos\MedTrack\backend\app\infrastructure\persistence\models'
files = glob.glob(f'{models_dir}/*.py')
modules = [os.path.basename(f)[:-3] for f in files if not os.path.basename(f).startswith('__')]

with open(os.path.join(models_dir, '__init__.py'), 'w') as f:
    for m in modules:
        f.write(f"import backend.app.infrastructure.persistence.models.{m}\n")
