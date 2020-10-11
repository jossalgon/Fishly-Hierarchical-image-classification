### 1
apt-get update && apt-get install -y wget zip && pip install fastai


### 2
%%js
var url = window.location.hostname + ':5901';
element.append('<a href="'+url+'">Open Remote Desktop</a>')

wget https://repo.anaconda.com/archive/Anaconda3-2020.07-Linux-x86_64.sh
chmod +x Anaconda3-2020.07-Linux-x86_64.sh
./Anaconda3-2020.07-Linux-x86_64.sh

# Data:
https://drive.google.com/a/go.ugr.es/uc?id=1dVBOBiqQeyFJ5ka81YnshGiqTEkKXDy4&export=download

conda install -c fastai -c pytorch -c anaconda fastai gh anaconda

# Abrir: /etc/fstab
tmpfs /dev/shm tmpfs defaults,size=60g 0 0
mount -o remount /dev/shm

# Notebooks:
https://drive.google.com/drive/folders/1Lb7kugpOcHduaKsrsmguczMJxDfr6Ope?usp=sharing

# En primer jupyter para coger token
!jupyter notebook list
