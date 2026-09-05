import Placeholder from "../components/Placeholder";
export default function Recommender() {
  return <Placeholder title="Smart Scheme Recommender" owner="A" notes={[
    "Profile form: income, caste, state, district, activity, amount needed",
    "Ranked scheme matches with per-condition pass/fail",
    "Provenance chip on every condition: source, authority, date fetched",
    "Enter income 4,20,000 to trigger the CONTRADICTORY_SOURCES verdict",
  ]} />;
}
