// Sample shop API server, written against Express 4.
const express = require('express');
const path = require('path');

const app = express();
app.use(express.json());

const products = [
  { id: 1, name: 'Field notebook', price: 12 },
  { id: 2, name: 'Trail mug', price: 18 },
];

app.get('/api/products', (req, res) => {
  res.json(products);
});

app.get('/api/products/:id', (req, res) => {
  const product = products.find((p) => p.id === Number(req.params.id));
  if (!product) {
    return res.status(404).json({ error: 'not found' });
  }
  res.json(product);
});

// Modern delete route — app.delete is the current API and must not be
// confused with the removed shorthand below.
app.delete('/api/products/:id', (req, res) => {
  res.status(204).end();
});

// Legacy route kept from the Express 3/4 era: it serves the download with
// the lowercase response helper that Express 5 removed.
app.get('/download/manual', (req, res) => {
  res.sendfile(path.join(__dirname, '..', 'public', 'manual.pdf'));
});

app.listen(3000, () => {
  console.log('sample-shop listening on http://localhost:3000');
});
