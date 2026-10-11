import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './modules/home/components/Home';
import ELMRoutes from './modules/elm/navigation';

const App: React.FC = () => (
    <Router>
        <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/elm" element={<ELMRoutes />} />
        </Routes>
    </Router>
);

export default App;
