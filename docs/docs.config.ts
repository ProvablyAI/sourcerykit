export interface ConfigItem {
	id: string;
	title?: string;
	icon?: string;
	pages?: ConfigItem[];
}

export interface RootConfig {
	pages: ConfigItem[];
}

const config: RootConfig = {
	pages: [
		{
			id: "getting_started",
			title: "Getting Started",
			icon: "Rocket",
			pages: [
				{ id: "introduction", title: "Introduction", icon: "BookOpen" },
				{ id: "end-to-end-walkthrough", icon: "Route" },
				{ id: "cli", icon: "Terminal" },
				{ id: "onboarding", icon: "UserPlus" },
			],
		},
		{
			id: "pillars",
			title: "Architecture & Pillars",
			icon: "BookOpen",
			pages: [
				{ id: "architecture", icon: "Blocks" },
				{ id: "intercept", icon: "Shield" },
				{ id: "trusted-endpoints", icon: "Lock" },
				{ id: "handoff", icon: "ArrowRightLeft" },
			],
		},
		{
			id: "cookbooks",
			title: "Cookbooks",
			icon: "ChefHat",
			pages: [
				{ id: "index", icon: "BookMarked" },
				{ id: "claude_agent", icon: "Blocks" },
				{ id: "langchain_agent", icon: "Blocks" },
				{ id: "openai_agents", icon: "Blocks" },
				{ id: "openai_agents_multi_agent", icon: "Blocks" },
				{ id: "claude_agent_multi_tool", icon: "Blocks" },
				{ id: "crewai_multi_agent", icon: "Blocks" },
				{ id: "langgraph_multi_agent", icon: "Blocks" },
			],
		},
		{
			id: "migrations",
			title: "Migration",
			icon: "ChefHat",
			pages: [{ id: "v1_0", icon: "BookMarked" }],
		},
		{
			id: "project",
			title: "Project",
			icon: "ChefHat",
			pages: [
				{ id: "CHANGELOG", icon: "History" },
				{ id: "CONTRIBUTING", icon: "GitPullRequest" },
				{ id: "LICENSE", icon: "Scale" },
			],
		},
	],
};

export default config;
