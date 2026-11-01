/* eslint-disable react/prop-types */
import { useAuth } from "../../context/AuthContext";
import { Navigate } from "react-router-dom";

const RequireAuth = ({children})=>{
    const {isAuthenticated } = useAuth();

    if(!isAuthenticated ){
        return <Navigate to="/login/" replace />
    }
    return children;
};

export default RequireAuth;