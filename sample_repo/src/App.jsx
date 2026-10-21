// Sample shop front end, already written in the React Router v6 style:
// Routes/Navigate/useNavigate throughout, none of the v5-only APIs.
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';

function HomePage() {
  const navigate = useNavigate();
  return (
    <main>
      <h1>Sample Shop</h1>
      <button onClick={() => navigate('/products')}>Browse products</button>
    </main>
  );
}

function ProductsPage() {
  return <h1>Products</h1>;
}

function NotFoundPage() {
  return <h1>Not found</h1>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/home" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
