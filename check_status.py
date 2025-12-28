import json
import glob
import os
from collections import defaultdict

DATA_DIR = 'data'

def check_status():
    stats = defaultdict(lambda: defaultdict(int)) # Stats[Fichier][Notoriété] = Nombre
    
    files = glob.glob(os.path.join(DATA_DIR, '*.json'))
    files.sort()
    
    print(f"{'FICHIER':<35} | {'N1 (Facile)':<12} | {'N2 (Moyen)':<12} | {'N3 (Dur)':<12} | {'TOTAL'}")
    print("-" * 85)
    
    for filepath in files:
        filename = os.path.basename(filepath)
        counts = {1: 0, 2: 0, 3: 0}
        total = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                for q in data:
                    noto = q.get('notoriety', 0)
                    if noto in counts:
                        counts[noto] += 1
                    total += 1
            except:
                pass
        
        # Code couleur simple (Si < 10 questions -> Alerte visuelle)
        n1_str = str(counts[1]) if counts[1] > 10 else f"⚠️ {counts[1]}"
        n2_str = str(counts[2]) if counts[2] > 10 else f"⚠️ {counts[2]}"
        n3_str = str(counts[3]) if counts[3] > 10 else f"⚠️ {counts[3]}"
        
        print(f"{filename:<35} | {n1_str:<12} | {n2_str:<12} | {n3_str:<12} | {total}")

if __name__ == "__main__":
    check_status()