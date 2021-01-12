import csv
import re
from pathlib import Path
from glob import glob
import pandas as pd
from sklearn.model_selection import train_test_split


DATA_PATH = Path('/home/jossalgon/Documentos/Master/scraper/families_3.csv')
IMAGES_PATH = Path('/home/jossalgon/Documentos/Master/images/')
EXPORT_PATH = Path('/home/jossalgon/Documentos/Master/Notebooks/families_3.csv')

def get_taxon_id_from_url(url):
    result = re.search(r".*\/taxa\/(\d+)-.*", url)
    return result.group(1)


def read_species():
    species = []
    file=open(DATA_PATH, "r")
    reader = csv.reader(file)
    next(reader, None)  # skip the headers
    for line in reader:
        specie_name = line[4]

        images = glob(str(IMAGES_PATH/specie_name)+'/*.jpg')
        images.extend(glob(str(IMAGES_PATH/specie_name)+'/*.png'))

        for img in images:
            img_path = str(img).replace(str(IMAGES_PATH)+'/', '')
            species.append({
                'Order': line[0],
                'Family': line[1],
                'Subfamily': line[2],
                'Genus': line[3],
                'Specie': specie_name,
                'fname': img_path
            })
    return species

species = read_species()
df = pd.DataFrame.from_dict(species)

df.to_csv(EXPORT_PATH, index=False)
