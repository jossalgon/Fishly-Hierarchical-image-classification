docker stop tfm-inaturalist && docker rm tfm-inaturalist
docker run -d --name=tfm-inaturalist \
        -v "/home/jossalgon/workspace/tfm/inaturalist":/myapp \
        -w /myapp \
        --net=container:nordvpn-es \
        buildkite/puppeteer \
        bash -c "export TZ=\"/usr/share/zoneinfo/Europe/Madrid\" && date && npm i && node index.js"
