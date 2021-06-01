################################################################################
##    FILE:  	cls-cost-categories-actions.py                                ##
##                                                                            ##
##    NOTES: 	Script with CostExplorerScripts class which supports          ##
##              `add-customer-gid-rule` and `remove-rule` actions             ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################


import json
import boto3 
import os

from simple_term_menu import TerminalMenu

class color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class CostExplorerScripts:
    """
    [summary]
    """
    def __init__(self, type: str = None) -> None:
        self.type = type 
        self.client = boto3.client('ce')
        self.category_arn = self.choose_cost_category()
        self.describe_category()
        
        if self.type: 
            if self.type == 'Add customer GID':
                self.operation_add_customer_gid_rule()
                
            elif self.type == 'Add basic rules':
                self.operation_add_basic_rule()
                
            elif self.type == 'Add service code rule':
                self.operation_add_service_code_rule()
                
            elif self.type == 'Remove rule':
                self.operation_remove_rule()

    #################################
    
    def operation_add_customer_gid_rule(self) -> None:
        try:
            customer_gid = input(f"{color.CYAN} - enter customer GID: {color.END}")
            customer_gid_rule = self.create_customer_gid_rule(customer_gid)
            self.add_rule_to_category(customer_gid_rule)
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with adding_customer_gid_rule method{color.END}")
            raise error

    def operation_add_basic_rule(self) -> None:
        try:
            basic_rule_to_add = self.choose_basic_rule()
            basic_rule = self.create_basic_rule(basic_rule_to_add)
            self.add_rule_to_category(basic_rule)
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with adding_customer_gid_rule method{color.END}")
            raise error
        
    def operation_add_service_code_rule(self) -> None:
        try:
            chosen_service = self.get_service_code_name()
            service_rule = self.create_service_rule(chosen_service)
            self.add_rule_to_category(service_rule)
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with adding_service_code method{color.END}")
            raise error

    def operation_remove_rule(self) -> None:
        try:
            rule_value_to_delete = self.choose_rule_value_to_delete()
            self.remove_rule_from_category(rule_value_to_delete)
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with removing_rule method{color.END}")
            raise error
            
    ##############################
    
    def choose_cost_category(self) -> str:
        try:
            cost_categories = []
            list_categories = self.client.list_cost_category_definitions()
            for category in list_categories['CostCategoryReferences']:
                category_name = category['Name']
                cost_categories.append(category_name)
            
            print(f"{color.CYAN} - choose cost category:{color.END}")
            if cost_categories:
                terminal_menu_choose_ce = TerminalMenu(cost_categories, title="Cost Categories:")
                terminal_menu_choose_ce.show()
                chosen_cost_category_name = terminal_menu_choose_ce.chosen_menu_entry
                for category in list_categories['CostCategoryReferences']:
                    if category['Name'] == chosen_cost_category_name:
                        chosen_cost_category_arn = category['CostCategoryArn']
                        return chosen_cost_category_arn
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with choose_cost_category{color.END}")
            raise error
        
        
    def describe_category(self) -> None:
        try:
            # print(f"{color.DARKCYAN} -- downloading current cost category structure{color.END}")
            self.describe_chosen_cost_category = self.client.describe_cost_category_definition(
                CostCategoryArn=self.category_arn
            )
            self.write_json(response=self.describe_chosen_cost_category)
            # print(f"{color.GREEN} --- saved successfully!{color.END}")
            
        except Exception as error:
            print(f"{color.RED}Encountered errors with describe_category{color.END}")
            raise error
        
        
    def write_json(self, response: dict, filename: str = 'out.json'):
        try:
            with open(filename, 'w') as self.file:
                json.dump(response, self.file, indent=1)
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with write_json{color.END}")
            raise error


    def add_rule_to_category(self, rule) -> None:
        try:
            # print(f"{color.DARKCYAN} -- updating cost category{color.END}")
            with open('out.json', 'r+') as file:
                body = json.load(file)
                json_body = body['CostCategory']['Rules']
                json_body.append(rule)
                self.client.update_cost_category_definition(
                    CostCategoryArn=self.category_arn,
                    RuleVersion='CostCategoryExpression.v1',
                    Rules=json_body
                )
                os.remove("out.json")
            
                print(f"{color.GREEN} --- updated successfully!{color.END}")
                
        except Exception as error:
            print(f"{color.RED}Encountered errors with add_customer_gid{color.END}")
            raise error
        
    ##############################
    
    @staticmethod
    def get_service_code_name() -> str:
        try:
            list_of_services = []
            pricing = boto3.client('pricing', region_name='us-east-1')
            for service in pricing.describe_services()['Services']:
                list_of_services.append(service['ServiceCode'])
            
            if list_of_services:
                print(f"{color.CYAN} - choose service to add:{color.END}")
                terminal_menu_choose_service = TerminalMenu(list_of_services, title="List of services:")
                terminal_menu_choose_service.show()
                chosen_service = terminal_menu_choose_service.chosen_menu_entry
                return chosen_service
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with get_service_code_name method{color.END}")
            raise error
        
    @staticmethod
    def create_service_rule(chosen_service) -> str:
        try:
            service_rule = 	{
                            "Value": "%s" % (chosen_service),
                            "Rule": {
                                "And": [
                                    {
                                        "Dimensions": {
                                            "Key": "SERVICE_CODE",
                                            "Values": [chosen_service],
                                            "MatchOptions": [
                                                "EQUALS"
                                            ]
                                        }
                                    },
                                    {
                                        "Dimensions": {
                                            "Key": "RECORD_TYPE",
                                            "Values": [
                                                "Usage"
                                            ],
                                            "MatchOptions": [
                                                "EQUALS"
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                
            if service_rule:
                return service_rule
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with create_service_rule method{color.END}")
            raise error       
    
    ##############################
    
    @staticmethod              
    def choose_basic_rule() -> str:
        try:
            basic_rules = ['Support', 'SavingsPlan', 'Tax', 'Credit']
            print(f"{color.CYAN} - choose basic rule value to add:{color.END}")
            terminal_menu_choose_basic_rule = TerminalMenu(basic_rules, title="Basic rules:")
            terminal_menu_choose_basic_rule.show()
            basic_rule_to_add = terminal_menu_choose_basic_rule.chosen_menu_entry
            return basic_rule_to_add
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with get_rule_values method{color.END}")
            raise error
        
    @staticmethod    
    def create_basic_rule(basic_rule_to_add) -> str:
        try:
            if basic_rule_to_add == 'Support':
                basic_rule = {
                                "Value": "Support",
                                "Rule": {
                                    "Dimensions": {
                                        "Key": "SERVICE_CODE",
                                        "Values": [
                                            "AWSSupportEnterprise",
                                            "AWSSupportBusiness",
                                            "AWSDeveloperSupport"
                                        ],
                                        "MatchOptions": [
                                            "EQUALS"
                                        ]
                                    }
                                }
                            }
            elif basic_rule_to_add == 'SavingsPlan':
                basic_rule = {
                                "Value": "Savings Plan",
                                "Rule": {
                                    "Dimensions": {
                                        "Key": "RECORD_TYPE",
                                        "Values": [
                                            "SavingsPlanRecurringFee"
                                        ],
                                        "MatchOptions": [
                                            "EQUALS"
                                        ]
                                    }
                                }
                            }
                
            elif basic_rule_to_add == 'Tax':
                basic_rule = {
                                "Value": "Tax",
                                "Rule": {
                                    "Dimensions": {
                                        "Key": "RECORD_TYPE",
                                        "Values": [
                                            "Tax"
                                        ],
                                        "MatchOptions": [
                                            "EQUALS"
                                        ]
                                    }
                                }
                            }
                
            elif basic_rule_to_add == 'Credit':
                basic_rule = {
                                "Value": "Credit",
                                "Rule": {
                                    "Dimensions": {
                                        "Key": "RECORD_TYPE",
                                        "Values": [
                                            "Credit"
                                        ],
                                        "MatchOptions": [
                                            "EQUALS"
                                        ]
                                    }
                                }
                            }
                
            else: 
                basic_rule = None
                
            if basic_rule is not None:
                return basic_rule
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with get_rule_values method{color.END}")
            raise error
        
    ##############################
    
    def choose_rule_value_to_delete(self) -> str:
        try:
            rule_values = []
            for rule in self.describe_chosen_cost_category['CostCategory']['Rules']:
                rule_values.append(rule['Value'])
            
            print(f"{color.CYAN} - choose rule value to delete:{color.END}")
            if rule_values:
                terminal_menu_choose_rule_value = TerminalMenu(rule_values, title="Rule Values:")
                terminal_menu_choose_rule_value.show()
                rule_value_to_delete = terminal_menu_choose_rule_value.chosen_menu_entry
                return rule_value_to_delete
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with get_rule_values method{color.END}")
            raise error


    def remove_rule_from_category(self, rule_value_to_delete) -> None:
        try:
            # print(f"{color.DARKCYAN} -- removing rule from cost category{color.END}")
            with open('out.json', 'r+') as file:
                body = json.load(file)
                json_updated = [obj for obj in body['CostCategory']['Rules'] if(obj['Value'] != rule_value_to_delete)]
                self.client.update_cost_category_definition(
                    CostCategoryArn=self.category_arn,
                    RuleVersion='CostCategoryExpression.v1',
                    Rules=json_updated
                )
                os.remove("out.json")
            
                print(f"{color.PURPLE} -- removed successfully!{color.END}")
                
        except Exception as error:
            print(f"{color.RED}Encountered errors with remove_rule_from_category method{color.END}")
            raise error
            
    ##############################
    
    def create_customer_gid_rule(self, customer_gid) -> str:
        try:
            sp_usage_type = self.define_sp_usage_type()
            customer_gid_rule_name = self.create_customer_gid_rule_name(customer_gid)
            rule = {
                        "Value": "%s" % (customer_gid_rule_name),
                        "Rule": {
                            "And": [
                                {
                                    "Tags": {
                                        "Key": "Customers",
                                        "Values": [
                                            "%s" % (customer_gid)
                                        ],
                                        "MatchOptions": [
                                            "CONTAINS"
                                        ]
                                    }
                                },
                                {
                                    "Tags": {
                                        "Key": "Env",
                                        "Values": [
                                            "prd",
                                            "prodtest",
                                            "sim",
                                            "uat"
                                        ],
                                        "MatchOptions": [
                                            "EQUALS"
                                        ]
                                    }
                                },
                                {
                                    "Dimensions": {
                                        "Key": "RECORD_TYPE",
                                        "Values": [
                                            "Usage",
                                            "%s" % (sp_usage_type),
                                            "RIFee"
                                        ],
                                        "MatchOptions": [
                                            "EQUALS"
                                        ]
                                    }
                                },
                                {
                                    "Dimensions": {
                                        "Key": "SERVICE_CODE",
                                        "Values": [
                                            "AmazonEC2"
                                        ],
                                        "MatchOptions": [
                                            "EQUALS"
                                        ]
                                    }
                                }
                            ]
                        }
                    }
            
            return rule
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with create_customer_gid_rule method{color.END}")
            raise error
        
    @staticmethod
    def define_sp_usage_type() -> str:
        try:
            print(f"{color.CYAN} - choose SP usage type{color.END}")
            terminal_menu_choose_sp = TerminalMenu(['Included', 'Excluded'], title="Savings plan usage type:")
            terminal_menu_choose_sp.show()
            chosen_sp_usage_type = terminal_menu_choose_sp.chosen_menu_entry
            
            if chosen_sp_usage_type == "Included": sp_usage_type = 'SavingsPlanCoveredUsage'
            elif chosen_sp_usage_type == "Excluded": sp_usage_type = 'DiscountedUsage'
            else: sp_usage_type = None
            
            if sp_usage_type is not None:
                return sp_usage_type
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with define_sp_usage_type method{color.END}")
            raise error
        
    @staticmethod    
    def create_customer_gid_rule_name(customer_gid) -> str:
        try:
            print(f"{color.CYAN} - define rule value name{color.END}")
            terminal_menu_choose_rule_value_name = TerminalMenu(['Yes', 'No'], title="Does the name include percents?")
            terminal_menu_choose_rule_value_name.show()
            is_rule_value_name_with_percents = terminal_menu_choose_rule_value_name.chosen_menu_entry
            
            if is_rule_value_name_with_percents == "Yes":
                rule_value_name_percents = input(f"{color.CYAN} - enter amount of percents [16,20,25,33,50,66,75,80]: {color.END}")
                rule_value_name = (f"{customer_gid} -- x {rule_value_name_percents} percents")
            elif is_rule_value_name_with_percents == "No":
                rule_value_name = customer_gid
            else: rule_value_name = customer_gid
            
            return rule_value_name
        
        except Exception as error:
            print(f"{color.RED}Encountered errors with create_customer_gid_rule_name method{color.END}")
            raise error

##########################################

if __name__ == '__main__':
    while True:
        terminal_menu_initial_choice = TerminalMenu(['Add customer GID', 'Add basic rules', 'Add service code rule', 'Remove rule', '==EXIT=='], title="Choose operation type")
        terminal_menu_initial_choice.show()
        operation_type = terminal_menu_initial_choice.chosen_menu_entry
        if operation_type == "==EXIT==":
            break
        else:
            CostExplorerScripts(type=operation_type)
        
            