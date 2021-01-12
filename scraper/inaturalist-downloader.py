import urllib.request, json
import shutil
from pathlib import Path
import requests
import math
import csv
import re
from fastprogress.fastprogress import progress_bar


LOCALE = 'es-ES'
PER_PAGE = 30
API_URL = f"https://api.inaturalist.org/v1/observations?verifiable=true&taxon_id=$TAXON_ID&locale={LOCALE}&order_by=votes&quality_grade=research&page=$PAGE_NUMBER&per_page={PER_PAGE}"
DATA_PATH = Path('/home/jossalgon/Documentos/Master/scraper/families_3.csv')
DST_FOLDER = Path('/home/jossalgon/Documentos/Master/scraper/images')


def read_species():
    species = []
    file=open(DATA_PATH, "r")
    reader = csv.reader(file)
    next(reader, None)  # skip the headers
    for line in reader:
        species.append({
            'name': line[4],
            'url': line[6]
        })
    return species


def get_taxon_id_from_url(url):
    result = re.search(r".*\/taxa\/(\d+)-.*", url)
    return result.group(1)


def download_photo(image_url, dst_path, image_name):
    Path(dst_path).mkdir(parents=True, exist_ok=True)
    r = requests.get(image_url, stream = True)
    if r.status_code == 200:
        r.raw.decode_content = True
        with open(dst_path/image_name,'wb') as f:
            shutil.copyfileobj(r.raw, f)
        return True
    else:
        return False

def get_num_of_pages(taxon_id):
    taxon_api_url = API_URL.replace('$TAXON_ID', str(taxon_id))
    taxon_api_url = taxon_api_url.replace('$PAGE_NUMBER', str(1))
    with urllib.request.urlopen(taxon_api_url) as url:
        data = json.loads(url.read().decode())
        total_results = data['total_results']
        return total_results

def download_photos(taxon_id, specie_name):
    total_results = get_num_of_pages(taxon_id)
    max_page = math.ceil(total_results/PER_PAGE)

    for page_num in range(0, max_page):
        taxon_api_url = API_URL.replace('$TAXON_ID', str(taxon_id))
        taxon_api_url = taxon_api_url.replace('$PAGE_NUMBER', str(page_num+1))
        with urllib.request.urlopen(taxon_api_url) as url:
            data = json.loads(url.read().decode())
            results = data['results']
            for result in results:
                for photo in result['photos']:
                    image_url = photo['url'].replace('square', 'large')
                    image_ext = '.png' if '.png' in image_url.lower() else '.jpg'
                    image_name = str(photo['id'])+image_ext
                    download_photo(image_url, DST_FOLDER/specie_name, image_name)


def main():
    species = read_species()
    for specie in progress_bar(species):
        taxon_id = get_taxon_id_from_url(specie['url'])
        download_photos(taxon_id, specie['name'])

if __name__ == "__main__":
    main()

# download_photos(49401)
