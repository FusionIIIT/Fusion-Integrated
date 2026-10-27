Fix pass (client). These are the TypeScript errors reported by `tsc --noEmit` after the previous steps. Fix them by editing the files shown. Do not delete functionality just to silence an error.

```
### tsc --noEmit
src/modules/leave/pages/ApplyLeavePage.tsx(3,3): error TS6133: 'ActionIcon' is declared but its value is never read.
src/modules/leave/pages/ApplyLeavePage.tsx(3,54): error TS6133: 'NumberInput' is declared but its value is never read.
src/modules/leave/pages/ApplyLeavePage.tsx(11,1): error TS6133: 'ErrorState' is declared but its value is never read.
src/modules/leave/pages/ApplyLeavePage.tsx(12,38): error TS2307: Cannot find module '../api/hooks' or its corresponding type declarations.
src/modules/leave/pages/ApplyLeavePage.tsx(13,39): error TS2307: Cannot find module '../api/types' or its corresponding type declarations.
src/modules/leave/pages/ApplyLeavePage.tsx(60,17): error TS7006: Parameter 'e' implicitly has an 'any' type.
src/modules/leave/pages/ApplyLeavePage.tsx(128,17): error TS2322: Type '{ label: string; value: string; onChange: (e: ChangeEvent<HTMLInputElement>) => void; placeholder: string; }' is not assignable to type 'IntrinsicAttributes & InputProps & ComponentProp<"input"> & Omit<Omit<DetailedHTMLProps<InputHTMLAttributes<HTMLInputElement>, HTMLInputElement>, "ref">, "component" | keyof InputProps> & { ...; }'.
  Property 'label' does not exist on type 'IntrinsicAttributes & InputProps & ComponentProp<"input"> & Omit<Omit<DetailedHTMLProps<InputHTMLAttributes<HTMLInputElement>, HTMLInputElement>, "ref">, "component" | keyof InputProps> & { ...; }'.
src/modules/leave/pages/ApplyLeavePage.tsx(145,11): error TS2322: Type '{ children: string; type: "button"; onClick: () => void; leftIcon: Element; loading: any; }' is not assignable to type 'IntrinsicAttributes & ButtonProps & ComponentProp<"button"> & Omit<Omit<DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement>, "ref">, "component" | keyof ButtonProps> & { ...; }'.
  Property 'leftIcon' does not exist on type 'IntrinsicAttributes & ButtonProps & ComponentProp<"button"> & Omit<Omit<DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement>, "ref">, "component" | keyof ButtonProps> & { ...; }'.
src/modules/leave/pages/ApprovalsPage.tsx(3,3): error TS6133: 'ActionIcon' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(8,1): error TS6133: 'errorMessage' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(12,29): error TS6133: 'useUnitHeadDecision' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(12,56): error TS2307: Cannot find module '../api/hooks' or its corresponding type declarations.
src/modules/leave/pages/ApprovalsPage.tsx(13,39): error TS2307: Cannot find module '../api/types' or its corresponding type declarations.
src/modules/leave/pages/ApprovalsPage.tsx(16,17): error TS6133: 'isPending' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(17,10): error TS6133: 'decisionFor' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(17,23): error TS6133: 'setDecisionFor' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(21,20): error TS6133: 'app' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(28,19): error TS6133: 'app' is declared but its value is never read.
src/modules/leave/pages/ApprovalsPage.tsx(48,32): error TS7006: Parameter 'app' implicitly has an 'any' type.
src/modules/leave/pages/ApprovalsPage.tsx(61,36): error TS2322: Type '{ children: string; color: "blue"; leftIcon: Element; onClick: () => void; }' is not assignable to type 'IntrinsicAttributes & ButtonProps & ComponentProp<"button"> & Omit<Omit<DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement>, "ref">, "component" | keyof ButtonProps> & { ...; }'.
  Property 'leftIcon' does not exist on type 'IntrinsicAttributes & ButtonProps & ComponentProp<"button"> & Omit<Omit<DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement>, "ref">, "component" | keyof ButtonProps> & { ...; }'.
src/modules/leave/pages/ApprovalsPage.tsx(67,35): error TS2322: Type '{ children: string; color: "red"; leftIcon: Element; onClick: () => void; }' is not assignable to type 'IntrinsicAttributes & ButtonProps & ComponentProp<"button"> & Omit<Omit<DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement>, "ref">, "component" | keyof ButtonProps> & { ...; }'.
  Property 'leftIcon' does not exist on type 'IntrinsicAttributes & ButtonProps & ComponentProp<"button"> & Omit<Omit<DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement>, "ref">, "component" | keyof ButtonProps> & { ...; }'.
src/modules/leave/pages/MyLeavesPage.tsx(8,1): error TS6133: 'errorMessage' is declared but its value is never read.
src/modules/leave/pages/MyLeavesPage.tsx(13,31): error TS2307: Cannot find module '../components/HistoryDrawer' or its corresponding type declarations.
src/modules/leave/pages/MyLeavesPage.tsx(14,60): error TS2307: Cannot find module '../api/hooks' or its corresponding type declarations.
src/modules/leave/pages/MyLeavesPage.tsx(15,33): error TS6196: 'LeaveBalance' is declared but never used.
src/modules/leave/pages/MyLeavesPage.tsx(15,53): error TS2307: Cannot find module '../api/types' or its corresponding type declarations.
src/modules/leave/pages/MyLeavesPage.tsx(19,42): error TS6133: 'balancesPending' is declared but its value is never read.
src/modules/leave/pages/MyLeavesPage.tsx(20,9): error TS6198: All destructured elements are unused.
src/modules/leave/pages/MyLeavesPage.tsx(25,21): error TS6133: 'app' is declared but its value is never read.
src/modules/leave/pages/MyLeavesPage.tsx(32,19): error TS6133: 'app' is declared but its value is never read.
src/modules/leave/pages/SubstituteRequestsPage.tsx(3,3): error TS6133: 'ActionIcon' is declared but its value is never read.
src/modules/leave/pages/SubstituteRequestsPage.tsx(3,15): error TS6133: 'Button' is declared but its value is never read.
src/modules/leave/```
