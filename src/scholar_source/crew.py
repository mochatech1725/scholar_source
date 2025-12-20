from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import SerperDevTool
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class ScholarSource():
    """ScholarSource crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def course_intelligence_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['course_intelligence_agent'], # type: ignore[index]
            verbose=True
        )

    @agent
    def resource_discovery_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['resource_discovery_agent'], # type: ignore[index]
            verbose=True,
            tools=[SerperDevTool()]
        )

    @agent
    def resource_validator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['resource_validator_agent'], # type: ignore[index]
            verbose=True
        )

    @agent
    def output_formatter_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['output_formatter_agent'], # type: ignore[index]
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def course_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['course_analysis_task'], # type: ignore[index]
        )

    @task
    def resource_search_task(self) -> Task:
        return Task(
            config=self.tasks_config['resource_search_task'], # type: ignore[index]
            output_file='report.md'
        )

    @task
    def resource_validation_task(self) -> Task:
        return Task(
            config=self.tasks_config['resource_validation_task'], # type: ignore[index]
        )
    
    @task
    def final_output_task(self) -> Task:
        return Task(
            config=self.tasks_config['final_output_task'], # type: ignore[index]
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
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
