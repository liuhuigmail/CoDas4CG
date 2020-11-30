# CoDas4CG
Contests based Dataset for Code Generation

If you are using the dataset, please cite the following paper: H. Liu, M. Shen, J. Zhu, N. Niu, G. Li and L. Zhang, "Deep Learning Based Program Generation from Requirements Text: Are We There Yet?," in IEEE Transactions on Software Engineering, doi: 10.1109/TSE.2020.3018481. Available at: https://ieeexplore.ieee.org/document/9173704


There are Seven folders: Compute, sql, Dataset, TestCases, Tools, CodeOfApproaches and GeneratedPrograms.

/Compute contains the file to compute bleu

/Dataset contains the programming tasks and their corresponding implementations in different programming languages. Each subfolder under /Datset corresponds to a single programming task. Notably, we do not include the commercial script to crawl data.

/TestCases contains the test cases for the programming tasks in folder /Dataset. The names of the subfolders in /TestCases specify the names of the programming tasks. According to such names you may find the corresponding tasks under /Dataset. Notably, such test cases are collected from programming contest websites, and we do not leverage test case generation tools.

/Tools contains the source code of our tool kit.

/GeneratedPrograms contains the programs generated by each approach.

/CodeOfApproaches Implementation of evaluated approaches.


**/sql Database contains the whole dataset (Python only). **

———

API for compute and sql:

Location	method	
sql			functions:
				
				RetrieveTasks(): Returns the description (requirements) of all tasks, each requirement is a text string
				
				RetrieveTask（ID）: Return the task description of the specified ID
				
				RetreiveImplementations（）：Return all codes, and each code corresponds to a python file.	
				
				RetreiveImplementations（ID）：Return all codes corresponding to the specified topic id, and each code corresponds to a python file.
				
				RetreiveTestCasess（ID）：Returns the test case corresponding to the specified question id.
	
				#To original data
					RetrieveTasks():select question from process_question 
					RetrieveTasks(ID): select question from process_question where numId = ID
					RetreiveImplementations（）:select code from process_implements 
					RetreiveImplementations（ID）:select code from process_implements where numId = ID
				#To processed data
					RetrieveTasks():select process_question from process_question 
					RetrieveTasks(ID): select process_question from process_question where numId = ID
					RetreiveImplementations（）:select process_code from process_implements 
					RetreiveImplementations（ID）:select process_code from process_implements where numId = ID
				#To test cases
					RetreiveTestCasess（ID）: select input,output from testcase where numId= ID

compute     functions:

				ComputeBLEU（pred, refer）:Calculate the BLEU between the generated code pred and the reference code refer	
				ComputeBLEU2（pred,refers）:Calculate the BLEU of code pred according to a series of refer	
				hasCompilerErrors（File name）:Check whether the code has static detection and dynamic compilation errors	
				PreProcessALL(File requirements， File implements): Return after preprocessing related requirements and codes	
				PreProcessReq(File requirements， File implements): Return after preprocessing related requirements
				PreProcessImp(File requirements， File implements): Return after preprocessing the relevant code	

