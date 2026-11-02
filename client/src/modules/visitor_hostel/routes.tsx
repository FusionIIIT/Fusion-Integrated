import React from 'react';
import { RouteObject, Navigate } from 'react-router-dom';

const BookingRequestPage = React.lazy(() => import('./pages/BookingRequestPage'));
const MyBookingsPage = React.lazy(() => import('./pages/MyBookingsPage'));
const CaretakerDashboardPage = React.lazy(() => import('./pages/CaretakerDashboardPage'));
const RoomAllotmentPage = React.lazy(() => import('./pages/RoomAllotmentPage'));
const MealsBookingPage = React.lazy(() => import('./pages/MealsBookingPage'));
const BillingSettlementPage = React.lazy(() => import('./pages/BillingSettlementPage'));
const InventoryPage = React.lazy(() => import('./pages/InventoryPage'));
const InChargeDashboardPage = React.lazy(() => import('./pages/InChargeDashboardPage'));

export const routes: RouteObject[] = [
  {
    index: true,
    element: <Navigate to="booking-request" replace />
  },
  {
    path: "booking-request",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <BookingRequestPage />
      </React.Suspense>
    )
  },
  {
    path: "my-bookings",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <MyBookingsPage />
      </React.Suspense>
    )
  },
  {
    path: "caretaker-dashboard",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <CaretakerDashboardPage />
      </React.Suspense>
    )
  },
  {
    path: "allotments",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <RoomAllotmentPage />
      </React.Suspense>
    )
  },
  {
    path: "meals",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <MealsBookingPage />
      </React.Suspense>
    )
  },
  {
    path: "billing",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <BillingSettlementPage />
      </React.Suspense>
    )
  },
  {
    path: "inventory",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <InventoryPage />
      </React.Suspense>
    )
  },
  {
    path: "incharge-dashboard",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <InChargeDashboardPage />
      </React.Suspense>
    )
  },
];
