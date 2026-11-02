import BatchSection from "./BatchSection";
import { PROGRAMME_CONFIG } from "../config/programmeConfig";

const PhDBatches = (props) => <BatchSection config={PROGRAMME_CONFIG.phd} {...props} />;

export default PhDBatches;
