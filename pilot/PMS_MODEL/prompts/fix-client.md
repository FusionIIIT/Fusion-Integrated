Fix pass (client). These are the TypeScript errors reported by `tsc --noEmit` after the previous steps. Fix them by editing the files shown. Do not delete functionality just to silence an error.

```
### tsc --noEmit
src/modules/patent/api.ts(2,40): error TS2307: Cannot find module './types' or its corresponding type declarations.
src/modules/patent/pages/AdminPage.tsx(3,3): error TS6133: 'ActionIcon' is declared but its value is never read.
src/modules/patent/pages/AdminPage.tsx(4,14): error TS6133: 'Select' is declared but its value is never read.
src/modules/patent/pages/AdminPage.tsx(7,1): error TS6192: All imports in import declaration are unused.
src/modules/patent/pages/AdminPage.tsx(11,1): error TS6133: 'ErrorState' is declared but its value is never read.
src/modules/patent/pages/AdminPage.tsx(14,38): error TS2307: Cannot find module '../api/hooks' or its corresponding type declarations.
src/modules/patent/pages/AdminPage.tsx(15,34): error TS2307: Cannot find module '../api/types' or its corresponding type declarations.
src/modules/patent/pages/AdminPage.tsx(60,6): error TS2741: Property 'onClose' is missing in type '{ children: Element; opened: boolean; title: string; size: "lg"; closeOnClickOutside: true; withCloseButton: true; }' but required in type 'ModalProps'.
src/modules/patent/pages/AdminPage.tsx(68,15): error TS2322: Type '{ children: string; order: number; }' is not assignable to type 'IntrinsicAttributes & TextProps & ComponentProp<"p"> & Omit<Omit<DetailedHTMLProps<HTMLAttributes<HTMLParagraphElement>, HTMLParagraphElement>, "ref">, "component" | keyof TextProps> & { ...; }'.
  Property 'order' does not exist on type 'IntrinsicAttributes & TextProps & ComponentProp<"p"> & Omit<Omit<DetailedHTMLProps<HTMLAttributes<HTMLParagraphElement>, HTMLParagraphElement>, "ref">, "component" | keyof TextProps> & { ...; }'.
src/modules/patent/pages/AdminPage.tsx(107,6): error TS2741: Property 'onClose' is missing in type '{ children: Element; opened: boolean; title: string; size: "lg"; closeOnClickOutside: true; withCloseButton: true; }' but required in type 'ModalProps'.
src/modules/patent/pages/AdminPage.tsx(115,15): error TS2322: Type '{ children: string; order: number; }' is not assignable to type 'IntrinsicAttributes & TextProps & ComponentProp<"p"> & Omit<Omit<DetailedHTMLProps<HTMLAttributes<HTMLParagraphElement>, HTMLParagraphElement>, "ref">, "component" | keyof TextProps> & { ...; }'.
  Property 'order' does not exist on type 'IntrinsicAttributes & TextProps & ComponentProp<"p"> & Omit<Omit<DetailedHTMLProps<HTMLAttributes<HTMLParagraphElement>, HTMLParagraphElement>, "ref">, "component" | keyof TextProps> & { ...; }'.
src/modules/patent/pages/AdminPage.tsx(117,16): error TS2322: Type '{ children: Element; orientation: string; gap: "xs"; }' is not assignable to type 'IntrinsicAttributes & GroupProps & RefAttributes<HTMLDivElement> & { component?: any; renderRoot?: ((props: Record<string, any>) => ReactNode) | undefined; }'.
  Property 'orientation' does not exist on type 'IntrinsicAttributes & GroupProps & RefAttributes<HTMLDivElement> & { component?: any; renderRoot?: ((props: Record<string, any>) => ReactNode) | undefined; }'.
src/modules/patent/pages/AdminPage.tsx(157,6): error TS2741: Property 'onClose' is missing in type '{ children: Element; opened: boolean; title: string; size: "lg"; closeOnClickOutside: true; withCloseButton: true; }' but required in type 'ModalProps'.
src/modules/patent/pages/AdminPage.tsx(165,15): error TS2322: Type '{ children: string; order: number; }' is not assignable to type 'IntrinsicAttributes & TextProps & ComponentProp<"p"> & Omit<Omit<DetailedHTMLProps<HTMLAttributes<HTMLParagraphElement>, HTMLParagraphElement>, "ref">, "component" | keyof TextProps> & { ...; }'.
  Property 'order' does not exist on type 'IntrinsicAttributes & TextProps & ComponentProp<"p"> & Omit<Omit<DetailedHTMLProps<HTMLAttributes<HTMLParagraphElement>, HTMLParagraphElement>, "ref">, "component" | keyof TextProps> & { ...; }'.
src/modules/patent/pages/AdminPage.tsx(170,46): error TS2345: Argument of type 'string | number' is not assignable to parameter of type 'SetStateAction<number | null>'.
  Type 'string' is not assignable to type 'SetStateAction<number | null>'.
src/modules/patent/pages/AdminPage.tsx(172,11): error TS2322: Type '{ label: string; value: number; onChange: (v: string | number) => void; step: number; precision: number; }' is not assignable to type 'IntrinsicAttributes & NumberInputProps & RefAttributes<HTMLInputElement> & { component?: any; renderRoot?: ((props: Record<...>) => ReactNode) | undefined; }'.
  Property 'precision' does not exist on type 'IntrinsicAttributes & NumberInputProps & RefAttributes<HTMLInputElement> & { component?: any; renderRoot?: ((props: Record<...>) => ReactNode) | undefined; }'.
src/modules/patent/pages/AdminPage.tsx(195,10): error TS2322: Type '{ children: ReactNode; orientation: string; gap: "xs"; }' is not assignable to type 'IntrinsicAttributes & GroupProps & RefAttributes<HTMLDivElement> & { component?: any; renderRoot?: ((props: Record<string, any>) => ReactNode) | undefined; }'.
  Property 'orientation' does not exist on type 'IntrinsicAttributes & GroupProps & RefAttributes<HTMLDivElement> & { component?: any; renderRoot?: ((props: Record<string, any>) => ReactNode) | undefined; }'.
src/modules/patent/pages/AdminPage.tsx(213,39): error TS6133: 'id' is declared but its value is never read.
src/modules/patent/pages/AdminPage.tsx(232,39): error TS6133: 'id' is declared but its value is never read.
src/modules/patent/pages/AdminPage.tsx(251,37): error TS6133: 'id' is declared but its value is never read.
src/modules/patent/pages/AdminPage.tsx(274,12): error TS2741: Property 'empty' is missing in type '{ rows: Application[]; loading: any; rowKey: (r: Application) => any; minWidth: number; columns: ({ key: string; header: string; render: (r: Application) => Element; } | { key: string; header: string; align: "right"; render: (r: Application) => Element; })[]; }' but required in type 'Props<Application>'.
src/modules/patent/pages/AdminPage.tsx(330,10): error TS2741: Property 'empty' is missing in type '{ rows: Ap```
