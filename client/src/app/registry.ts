export interface ModuleManifest {
  code: string;
  basePath: string;
  load: () => Promise<{ routes: RouteObject[] }>;
}

const modules: ModuleManifest[] = [
  // Other modules...
  {
    code: 'elm',
    basePath: '/modules/elm',
    load: () => import('./modules/elm'),
  },
];

export default modules;
