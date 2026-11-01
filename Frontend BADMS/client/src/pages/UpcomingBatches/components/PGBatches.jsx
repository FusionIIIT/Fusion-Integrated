import BatchSection from "./BatchSection";
import { PROGRAMME_CONFIG } from "../config/programmeConfig";

const PGBatches = (props) => <BatchSection config={PROGRAMME_CONFIG.pg} {...props} />;

export default PGBatches;
