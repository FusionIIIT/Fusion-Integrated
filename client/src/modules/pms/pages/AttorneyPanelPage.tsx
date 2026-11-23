import { useEndPanelAttorney, usePanel, useSetPanelAttorney } from "../api/hooks";
import { RosterPage } from "../components/RosterPage";

// UC-PMS-026: the approved attorney panel and each attorney's areas.
export default function AttorneyPanelPage() {
  return <RosterPage title="Attorney Panel" who="panel attorney"
    subtitle="Approved attorneys and their areas of expertise" roster={usePanel()}
    save={useSetPanelAttorney()} end={useEndPanelAttorney()} />;
}
