import { RouteObject } from 'react-router-dom';
import { modules } from './registry';

const routes: RouteObject[] = [
  // Other routes...
  ...modules.flatMap(module => module.routes),
];

export default routes;
