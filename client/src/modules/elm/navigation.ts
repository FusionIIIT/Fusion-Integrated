import { Route, Routes } from 'react-router-dom';
import CourseList from './components/CourseList';

const ELMRoutes: React.FC = () => (
    <Routes>
        <Route path="/elm/courses" element={<CourseList />} />
    </Routes>
);

export default ELMRoutes;
