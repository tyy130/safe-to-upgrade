// Small helpers built on lodash. lodash has no entry in the breaking-change
// data set used for the demo, so its verdict is UNKNOWN — never guessed.
const _ = require('lodash');

function groupProductsByName(products) {
  return _.groupBy(products, 'name');
}

function productNames(products) {
  return _.map(products, 'name');
}

module.exports = { groupProductsByName, productNames };
