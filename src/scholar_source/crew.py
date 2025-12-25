from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import (
    SerperDevTool,
    WebsiteSearchTool,
    YoutubeVideoSearchTool
)
from typing import List
import os
from scholar_source.tools import WebPageFetcherTool

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class ScholarSource():
    """ScholarSource crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def course_intelligence_agent(self) -> Agent:
        agent_config = self.agents_config['course_intelligence_agent']  # type: ignore[index]
        # Override LLM from environment variable if set
        model = os.getenv('COURSE_INTELLIGENCE_AGENT_MODEL', agent_config.get('llm', 'openai/gpt-4o'))
        return Agent(
            config=agent_config,
            llm=model,
            verbose=True,
            tools=[
                WebPageFetcherTool(),  # For fetching full page content
                WebsiteSearchTool()     # For searching within pages if needed
            ]
        )

    @agent
    def resource_discovery_agent(self) -> Agent:
        agent_config = self.agents_config['resource_discovery_agent']  # type: ignore[index]
        # Override LLM from environment variable if set
        model = os.getenv('RESOURCE_DISCOVERY_AGENT_MODEL', agent_config.get('llm', 'openai/gpt-4o-mini'))
        return Agent(
            config=agent_config,
            llm=model,
            verbose=True,
            tools=[SerperDevTool()]
        )

    @agent
    def resource_validator_agent(self) -> Agent:
        agent_config = self.agents_config['resource_validator_agent']  # type: ignore[index]
        # Override LLM from environment variable if set
        model = os.getenv('RESOURCE_VALIDATOR_AGENT_MODEL', agent_config.get('llm', 'openai/gpt-4o-mini'))
        return Agent(
            config=agent_config,
            llm=model,
            verbose=True,
            tools=[
                WebsiteSearchTool(),  # For validating web pages
                YoutubeVideoSearchTool()  # For validating YouTube videos
            ]
        )

    @agent
    def output_formatter_agent(self) -> Agent:
        agent_config = self.agents_config['output_formatter_agent']  # type: ignore[index]
        # Override LLM from environment variable if set
        model = os.getenv('OUTPUT_FORMATTER_AGENT_MODEL', agent_config.get('llm', 'openai/gpt-4o-mini'))
        return Agent(
            config=agent_config,
            llm=model,
            verbose=True
        )

    @task
    def course_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['course_analysis_task'],
        )

    @task
    def resource_search_task(self) -> Task:
        return Task(
            config=self.tasks_config['resource_search_task'], 
            output_file='report.md'
        )

    @task
    def resource_validation_task(self) -> Task:
        return Task(
            config=self.tasks_config['resource_validation_task'],
        )
    
    @task
    def final_output_task(self) -> Task:
        return Task(
            config=self.tasks_config['final_output_task'],
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ScholarSource crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            max_iter=int(os.getenv('MAX_CREW_ITERATIONS', '15')),  # Read from environment or default to 15
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
