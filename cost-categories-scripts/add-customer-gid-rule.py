################################################################################
##    FILE:  	add-customer-gid-rule.py                                      ##
##                                                                            ##
##    NOTES: 	Script allowing to add a new cost category rule with          ##
##              Customer GID                                                  ##
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


def create_customer_gid_rule(customer_gid: str = None) -> str:
    try:
        sp_usage_type = define_sp_usage_type()
        rule_value_name = create_customer_gid_rule_name(customer_gid)
        rule = {
                    "Value": "%s" % (rule_value_name),
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
        print(f"{color.RED}Encountered errors with create_rule_for_customer{color.END}")
        raise error


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
        print(f"{color.RED}Encountered errors with get_sp_usage_type{color.END}")
        raise error
    
    
def create_customer_gid_rule_name(customer_gid: str = None) -> str:
    try:
        print(f"{color.CYAN} - define rule value name{color.END}")
        terminal_menu_choose_rule_value_name = TerminalMenu(['Yes', 'No'], title="Does the name include percents?")
        terminal_menu_choose_rule_value_name.show()
        is_rule_value_name_with_percents = terminal_menu_choose_rule_value_name.chosen_menu_entry
        
        if is_rule_value_name_with_percents == "Yes":
            rule_value_name_percents = input(f"{color.CYAN} - enter amount of percents [16,20,25,33,50,66,75,80]: {color.END}")
            rule_value_name = (f"{customer_gid} -- x {rule_value_name_percents} percents")
        elif is_rule_value_name_with_percents == "No": rule_value_name = customer_gid
        else: rule_value_name = customer_gid
        
        return rule_value_name
    
    except Exception as error:
        print(f"{color.RED}Encountered errors with get_rule_value_name{color.END}")
        raise error
    
    
def write_json(response: dict, filename: str = 'out.json') -> None:
    try:
        with open(filename, 'w') as file:
            json.dump(response, file, indent=1)
    
    except Exception as error:
        print(f"{color.RED}Encountered errors with write_json{color.END}")
        raise error

def choose_cost_category() -> str:
    try:
        cost_categories = []
        list_categories = client.list_cost_category_definitions()
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
    
def describe_category(category_arn: str = None) -> None:
    try:
        print(f"{color.DARKCYAN} -- saving current cost category json body{color.END}")
        describe_chosen_cost_category = client.describe_cost_category_definition(
            CostCategoryArn=category_arn
        )
        write_json(response=describe_chosen_cost_category)
        print(f"{color.GREEN} --- saved successfully!{color.END}")
        
    except Exception as error:
        print(f"{color.RED}Encountered errors with describe_category{color.END}")
        raise error

def add_customer_gid_rule(category_arn: str = None, customer_gid: str = None) -> None:
    try:
        print(f"{color.DARKCYAN} -- creating rule{color.END}")
        rule = create_customer_gid_rule(customer_gid)
        print(f"{color.DARKCYAN} -- updating cost category{color.END}")
        with open('out.json', 'r+') as file:
            body = json.load(file)
            json_body = body['CostCategory']['Rules']
            json_body.append(rule)
            client.update_cost_category_definition(
                CostCategoryArn=category_arn,
                RuleVersion='CostCategoryExpression.v1',
                Rules=json_body
            )
            os.remove("out.json")
        
        print(f"{color.GREEN} --- updated successfully!{color.END}")
            
    except Exception as error:
        print(f"{color.RED}Encountered errors with add_customer_gid_rule{color.END}")
        raise error
    
##########################################

def main_sequence() -> None:
    try:
        customer_gid = input(f"{color.CYAN} - enter customer GID: {color.END}")
        category_arn = choose_cost_category()
        describe_category(category_arn)
        add_customer_gid_rule(category_arn, customer_gid)
    
    except Exception as error:
        print(f"{color.RED}Encountered errors with main_sequence{color.END}")
        raise error

##########################################

if __name__ == '__main__':
    client = boto3.client('ce')
    main_sequence()