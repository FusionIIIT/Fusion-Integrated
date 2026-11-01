import { doc, setDoc } from "firebase/firestore";
import { db } from "../firebaseConfig"; 

export const saveUserData = async (uid, email, username) => {
  try {
    await setDoc(doc(db, "users", uid), {
      email,
      username,
      lastLogin: new Date().toISOString(),
    });
    console.log("User data saved successfully");
  } catch (error) {
    console.error("Error saving user data:", error.message);
  }
};
