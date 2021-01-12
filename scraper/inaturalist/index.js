require('console-stamp')(console, 'HH:MM:ss');
const puppeteer = require('puppeteer');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const fs = require('fs');

const csvWriter = createCsvWriter({
  path: 'inaturalist.csv',
  header: [
    {id: 'order', title: 'Order'},
    {id: 'family', title: 'Family'},
    {id: 'subfamily', title: 'Subfamily'},
    {id: 'genus', title: 'Genus'},
    {id: 'specie', title: 'Specie'},
    {id: 'observations', title: 'Observations'},
    {id: 'url', title: 'url'},
  ]
});

process.setMaxListeners(Infinity);


async function run(browser, url, classField) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1366, height: 900});

  const headers = {'accept-language': 'es-ES,es;q=0.9,en;q=0.8', 'accept-encoding': 'gzip, deflate, br', 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
  'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36'};
  page.setExtraHTTPHeaders(headers);
  const response = await page.goto(url, {waitUntil: 'networkidle2', timeout: 0});

  // CLICK OVER TAXONOMY BUTTON
  const [button] = await page.$x("//a[contains(., 'Taxonomía')]");
  if (button) {
      await button.click();
  }

  // GET ELEMENTS BY THE CLASS FIELD
  const elements = await page.$x(`//a[contains(@class, 'sciname') and contains(@class, '${classField}')]`);
  if (elements.length > 0) {
    // GENERATE THE RESULT WITH THE NAME AND URL OF THE ELEMENTS
    let results = await page.evaluate((...elements) => {
        return elements.map((e, i) => [e.textContent, e.href]);
      }, ...elements);

    // ADD NUMBER OF OBSERVATIONS TO THE RESULT
    const num_observations_element = await page.$x(`//li[not(contains(@class, 'hidable'))]/div/div[contains(@class, 'label-obs-count')]`);
    const num_observations = await page.evaluate((...num_observations_element) => {
        return num_observations_element.map(e => e.textContent.replace('.',''));
      }, ...num_observations_element);
    for (let i = 0; i < results.length; i++) {
      results[i].push(parseInt(num_observations[i]));
    }

    // CLOSE BROWSER AND RETURN RESULTS
    await page.close();
    return results
  } else {
    // IF NO ELEMENTS WAS FOUND RETURN AN EMPTY ARRAY
    await page.close();
    return []
  }
}

;(async () => {
  const rows = []

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', 'enable-logging', '--v=1']
  });

  // LOOP OVER FISHES
  const orders = await run(browser, 'https://www.inaturalist.org/taxa/47178-Actinopterygii#taxonomy-tab', 'order');
  const initial = 0;
  const final = 2;
  console.log(`RUNNING FROM ${initial} TO ${final} OF TOTAL ${orders.length}.`)
  for (let i = initial; i < final; i++) {
    console.log(`>   ORDER: ${i+1} of ${final}.`)
    const orderName = orders[i][0].replace('orden', '').trim();
    const orderUrl = orders[i][1];

    // LOOP OVER FAMILIES
    const families = await run(browser, orderUrl, 'family');
    for (let i = 0; i < families.length; i++) {
      const familyName = families[i][0].replace('Familia', '').trim();
      const familyUrl = families[i][1];
      const family_num_observations = families[i][2];
      console.log(`>>>   FAMILY: ${i+1} of ${families.length}. [OBSERVATIONS: ${family_num_observations}]`)

      // LOOP OVER SUBFAMILIES
      let subfamilies = await run(browser, familyUrl, 'subfamily');
      // IF IT HAS SUBFAMILIES
      if (subfamilies.length > 0) {
        for (let i = 0; i < subfamilies.length; i++) {
          const subfamilyName = subfamilies[i][0].replace('subfamilia', '').trim();
          const subfamilyUrl = subfamilies[i][1];

          // LOOP OVER GENERA
          const genera = await run(browser, subfamilyUrl, 'genus');
          for (let i = 0; i < genera.length; i++) {
            const genusName = genera[i][0].replace('género', '').trim();
            const genusUrl = genera[i][1];

            // LOOP OVER SPECIES
            const species = await run(browser, genusUrl, 'species');
            for (let i = 0; i < species.length; i++) {
              const specieName = species[i][0];
              const specieUrl = species[i][1];
              const num_observations = species[i][2];
              const row = {
                'order': orderName,
                'family': familyName,
                'subfamily': subfamilyName,
                'genus': genusName,
                'specie': specieName,
                'observations': num_observations,
                'url': specieUrl
              }
              rows.push(row)
              // console.log(row);
            }
          }
        }
      // IF IT HAS NOT SUBFAMILIES
      } else {

        // LOOP OVER GENERA
        const genera = await run(browser, familyUrl, 'genus');
        for (let i = 0; i < genera.length; i++) {
          const genusName = genera[i][0].replace('género', '').trim();
          const genusUrl = genera[i][1];

          // LOOP OVER SPECIES
          const species = await run(browser, genusUrl, 'species');
          for (let i = 0; i < species.length; i++) {
            const specieName = species[i][0];
            const specieUrl = species[i][1];
            const num_observations = species[i][2];
            const row = {
              'order': orderName,
              'family': familyName,
              'subfamily': null,
              'genus': genusName,
              'specie': specieName,
              'observations': num_observations,
              'url': specieUrl
            }
            rows.push(row)
            // console.log(row);
          }
        }
      }
    }
  }
  browser.close();

  csvWriter.writeRecords(rows).then(
    () => console.log('The CSV file was written successfully')
  );
})()
