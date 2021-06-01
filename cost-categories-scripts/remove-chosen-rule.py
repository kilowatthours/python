################################################################################
##    FILE:  	remove-chosen-rule.py                                         ##
##                                                                            ##
##    NOTES: 	Script allowing to remove cost category rule                  ##
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
    
def choose_rule_value_to_delete(category_arn: str = None) -> str:
    try:
        rule_values = []
        describe_chosen_cost_category = client.describe_cost_category_definition(
            CostCategoryArn=category_arn
        )
        
        for rule in describe_chosen_cost_category['CostCategory']['Rules']:
            rule_values.append(rule['Value'])
        
        print(f"{color.CYAN} - choose rule value to delete:{color.END}")
        if rule_values:
            terminal_menu_choose_rule_value = TerminalMenu(rule_values, title="Rule Values:")
            terminal_menu_choose_rule_value.show()
            rule_value_to_delete = terminal_menu_choose_rule_value.chosen_menu_entry
            return rule_value_to_delete
    
    except Exception as error:
        print(f"{color.RED}Encountered errors with get_rule_values{color.END}")
        raise error
    
def describe_category(category_arn: str = None) -> None:
    try:
        print(f"{color.DARKCYAN} -- saving current cost category json body{color.END}")
        describe_chosen_cost_category = client.describe_cost_category_definition(
            CostCategoryArn=category_arn
        )
        write_json(response=describe_chosen_cost_category)
        
    except Exception as error:
        print(f"{color.RED}Encountered errors with describe_category{color.END}")
        raise error

def remove_rule_from_category(category_arn: str = None, rule_value_to_delete: str = None) -> None:
    try:
        print(f"{color.DARKCYAN} -- removing rule from cost category{color.END}")
        with open('out.json', 'r+') as file:
            body = json.load(file)
            json_updated = [obj for obj in body['CostCategory']['Rules'] if(obj['Value'] != rule_value_to_delete)]
            client.update_cost_category_definition(
                CostCategoryArn=category_arn,
                RuleVersion='CostCategoryExpression.v1',
                Rules=json_updated
            )
            os.remove("out.json")
        
            print(f"{color.PURPLE} -- removed successfully!{color.END}")
            
    except Exception as error:
        print(f"{color.RED}Encountered errors with remove_rule_from_category{color.END}")
        raise error
    
##########################################

def main_sequence() -> None:
    try:
        category_arn = choose_cost_category()
        describe_category(category_arn)
        rule_value_to_delete = choose_rule_value_to_delete(category_arn)
        remove_rule_from_category(category_arn, rule_value_to_delete)
    
    except Exception as error:
        print(f"{color.RED}Encountered errors with main_sequence{color.END}")
        raise error

##########################################

if __name__ == '__main__':
    client = boto3.client('ce')
    main_sequence()