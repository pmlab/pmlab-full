# pmlab-full
Process Mining scripting environment
PMLAB is an interactive programming environment for (exploratory) process
mining computing and/or research on top of a process-oriented language. In this
language, logs, models and many other high-level objects/tasks are first-class citizens, 
meaning that one can compute (interactively or not) on the basis of these
elements. Importantly, there can be different granularities on the view of these
high-level elements, e.g., a log can be simply passed to a discovery algorithm
(coarse-level view), or analyzed to derive the most frequent cases (introspective
view). The following is a list of PMLAB features:

– Interactive shell: as happens in Mathematica, a shell where every object
used/computed is available is provided, and process mining algorithms may
be applied to these objects to create new ones. The typical session may
start by importing the libraries to be used, and to continuously enrich the
environment by computing new objects from the existing ones.

– Process mining elements as first-class citizens of the language: importantly,
the environment offers a solid and consistent library for some of the main
tasks required in process mining, e.g., importing a log in XES format. Once
a log is imported into a variable, algorithms can be applied on the variable to
produce new elements (e.g., a discovery algorithm to derive a BPMN model).

– Programmer friendly: the environment not only provides the necessary help
for using the elements, but more importantly describes them in a way a
programmer can incorporate these objects onto her/his programs.

– Extendable: new functionalities can be added by means of new library modules.

– Irredundant: to have thirty algorithms to perform the same task maybe is
not the ideal situation for using that functionality. As a policy, we believe
the core environment should limit the amount of redundancy in order to
simplify the usage.

– Simple Programming: the syntax and semantics of the language should be
easy, in order to allow for easy programming. One example of this is types in
programming languages: although useful for programming and compilation,
the learning curve required to master a statically-typed language is significantly 
higher than the one for a dynamically-typed language. This makes
dynamically-typed languages as Python a good candidate.

– OS exposed: there is a good marriage between the operating system elements
(files, directories, databases, etc ...) and the elements of the environment.
This will easy the management and manipulation of the data within the
environment.

– With support to distributed/parallel computing: it is fairly easy to distribute
or parallelize the computations to take advantage of the computing resources
available.


# Installation

See pmlab/doc/pm_guide.pdf for detailed instructions for installation.

