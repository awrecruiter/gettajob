export type ResourceItem = {
  title: string;
  url: string;
  description: string;
};

export type ResourceCategory = {
  name: string;
  description: string;
  items: ResourceItem[];
};

export const RESOURCES: ResourceCategory[] = [
  {
    name: "Find primes winning federal work",
    description:
      "Public data sources that reveal who's holding contracts, who's spending federal dollars, and which small businesses are on the map.",
    items: [
      {
        title: "USAspending.gov",
        url: "https://www.usaspending.gov",
        description:
          "Federal spend data — search by keyword, NAICS, or agency. Shows prime and subaward history.",
      },
      {
        title: "GSA eLibrary",
        url: "https://www.gsaelibrary.gsa.gov",
        description:
          "Which vendors hold which GSA contract vehicles (Schedules, GWACs, IDIQs).",
      },
      {
        title: "SAM.gov Entity Search",
        url: "https://sam.gov/entity-registration",
        description:
          "Registered federal contractor lookup — SAM.gov is the master registry.",
      },
      {
        title: "SBA Dynamic Small Business Search (DSBS)",
        url: "https://dsbs.sba.gov/search/dsp_dsbs.cfm",
        description:
          "Profiles of certified small businesses — filter by NAICS, size, or set-aside status.",
      },
    ],
  },
  {
    name: "Prime supplier portals",
    description:
      "Vendor-registration pages for major defense and civilian primes. Register once per prime to be visible to their teaming leads.",
    items: [
      {
        title: "Lockheed Martin",
        url: "https://www.lockheedmartin.com/en-us/suppliers.html",
        description: "Supplier portal and procurement contacts.",
      },
      {
        title: "Boeing",
        url: "https://www.boeing.com/suppliers",
        description: "Supplier registration and current opportunities.",
      },
      {
        title: "Raytheon Technologies (RTX)",
        url: "https://www.rtx.com/suppliers",
        description: "Supplier registration across RTX business units.",
      },
      {
        title: "Northrop Grumman",
        url: "https://www.northropgrumman.com/suppliers",
        description: "Supplier registration and diversity programs.",
      },
      {
        title: "General Dynamics",
        url: "https://www.generaldynamics.com",
        description: "Business-unit supplier portals — navigate to Suppliers.",
      },
      {
        title: "L3Harris",
        url: "https://www.l3harris.com/suppliers",
        description: "Supplier resources and registration.",
      },
      {
        title: "Leidos",
        url: "https://www.leidos.com",
        description: "Navigate to Company → Small Business / Suppliers.",
      },
      {
        title: "Booz Allen Hamilton",
        url: "https://www.boozallen.com",
        description:
          "Navigate to Expertise → Supplier Diversity for the teaming program.",
      },
      {
        title: "SAIC",
        url: "https://www.saic.com",
        description: "Navigate to About → Suppliers.",
      },
      {
        title: "CACI",
        url: "https://www.caci.com",
        description: "Navigate to Suppliers / Small Business.",
      },
    ],
  },
  {
    name: "Agency small-business offices (OSDBUs)",
    description:
      "The person at each agency who connects small firms with prime awardees.",
    items: [
      {
        title: "SBA — federal contracting support",
        url: "https://www.sba.gov/federal-contracting",
        description:
          "SBA's federal-contracting hub. Includes the OSDBU directory across all agencies.",
      },
      {
        title: "DoD Office of Small Business Programs",
        url: "https://business.defense.gov",
        description:
          "DoD-wide small business programs, forecasts, and matchmaking events.",
      },
      {
        title: "NASA OSBP",
        url: "https://osbp.nasa.gov",
        description: "NASA small business office and procurement forecasts.",
      },
      {
        title: "VA OSDBU",
        url: "https://www.va.gov/osdbu",
        description: "VA small business office with veteran-owned focus.",
      },
      {
        title: "DHS Small Business",
        url: "https://www.dhs.gov",
        description: "Navigate to Business → Small Business Resources.",
      },
    ],
  },
  {
    name: "Events, forecasts, pipeline",
    description:
      "Where solicitations get previewed before they post. Reaching a prime before the RFP goes public is the whole point.",
    items: [
      {
        title: "SAM.gov Contract Opportunities",
        url: "https://sam.gov/opportunities/",
        description:
          "Active and upcoming federal opportunities. Filter by NAICS and set-aside.",
      },
      {
        title: "Acquisition Gateway (GSA)",
        url: "https://acquisitiongateway.gov",
        description:
          "Federal buyers, market research, and forecasts under one roof.",
      },
      {
        title: "PSC events calendar",
        url: "https://www.pscouncil.org/events",
        description: "Professional Services Council — federal-industry events.",
      },
      {
        title: "GovConWire",
        url: "https://www.govconwire.com",
        description:
          "News and event coverage across defense and civilian contracting.",
      },
      {
        title: "GovCon Giants (Eric Coffie)",
        url: "https://govcongiants.com",
        description:
          "Small-business GovCon guide — the source of the '10 places to find subcontracting' infographic.",
      },
    ],
  },
  {
    name: "Partnerships and set-aside programs",
    description:
      "Federal programs designed to team small firms with primes or grant preferential access to contracts.",
    items: [
      {
        title: "SBA Mentor-Protégé Program",
        url: "https://www.sba.gov/federal-contracting/contracting-assistance-programs/all-small-mentor-protege-program",
        description:
          "Formal 6-year mentorship between primes and small firms.",
      },
      {
        title: "8(a) Business Development",
        url: "https://www.sba.gov/federal-contracting/contracting-assistance-programs/8a-business-development-program",
        description:
          "Set-aside program for socially and economically disadvantaged firms.",
      },
      {
        title: "SBA contracting assistance overview",
        url: "https://www.sba.gov/federal-contracting/contracting-assistance-programs",
        description: "All SBA set-aside and support programs in one place.",
      },
    ],
  },
  {
    name: "Trade associations and consortia",
    description:
      "Where teaming conversations happen and RFPs get discussed before they post. Membership fees vary.",
    items: [
      {
        title: "AFCEA",
        url: "https://www.afcea.org",
        description:
          "Armed Forces Communications and Electronics Association — defense IT and comms.",
      },
      {
        title: "NDIA",
        url: "https://www.ndia.org",
        description: "National Defense Industrial Association — broad defense industry.",
      },
      {
        title: "PSC",
        url: "https://www.pscouncil.org",
        description:
          "Professional Services Council — federal services and consulting.",
      },
      {
        title: "ACT-IAC",
        url: "https://www.actiac.org",
        description:
          "American Council for Technology / Industry Advisory Council — federal IT.",
      },
      {
        title: "AIAA",
        url: "https://www.aiaa.org",
        description:
          "American Institute of Aeronautics and Astronautics — aerospace and defense R&D.",
      },
    ],
  },
];
