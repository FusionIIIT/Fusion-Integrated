import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const apiKey = import.meta.env.VITE_API_KEY;
const authDomain = import.meta.env.VITE_AUTH_DOMAIN;

const firebaseConfig = {
    apiKey: apiKey,
    authDomain: authDomain,
    projectId: "fusion-system-admin",
    storageBucket: "fusion-system-admin.firebasestorage.app",
    messagingSenderId: "315737830873",
    appId: "1:315737830873:web:060aac2555855892e9d5c8"
  };

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);