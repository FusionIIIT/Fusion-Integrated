import { useDirectors, useEndDirector, useSetDirector } from "../api/hooks";
import { RosterPage } from "../components/RosterPage";

// PMS-AFR-222, ruling C13: Directors and the technical areas they review.
export default function DirectorsPage() {
  return <RosterPage title="Directors" who="Director"
    subtitle="Who reviews which technical areas" roster={useDirectors()}
    save={useSetDirector()} end={useEndDirector()} />;
}
