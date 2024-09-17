# ALEA AI Web Survey

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/alea-web-survey.svg)](https://pypi.org/project/alea-web-survey/)

## Description

We are collecting data for research on the legal and ethical impact of AI on the Web and society.  While the survey
and [research agenda](https://aleainstitute.ai) are still evolving as we learn, we are making the survey
source code and intermediate data available to the public for transparency and to encourage collaboration.


## Polite Data Collection

Because other existing public datasets are not sufficient for our research or up-to-date, we are collecting our own data.

We are committed to collecting data in a polite and respectful manner that minimizes network impact.  This framework
is designed to minimize network and resource impact by only retrieving the minimum set of data necessary for our research.

Where possible, raw HTTP requests are made to retrieve content.  When pages like `/` or a ToS/legal page is only
available via JavaScript, we use a headless browser to retrieve the content, which may result in additional network
requests based on your site's configuration.

We are not scraping or indexing full sites.  We are limited to retrieving the following data:

 * /robots.txt
 * /ai.txt
 * /humans.txt
 * /security.txt
 * /, used to identify any terms of services or other key legal pages
 * Any sitemap resources listed in /robots.txt, used to identify any terms of services or other key legal pages
 * Any terms of service or legal pages as identified above

## License

This ALEA project is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions about this ALEA project, please [open an issue](https://github.com/alea-institute/alea-web-survey/issues) on GitHub.

## Learn More

To learn more about ALEA and its software and research projects like KL3M, visit the [ALEA website](https://aleainstitute.ai/).
