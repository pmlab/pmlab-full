import pygame, sys, threading
from pygame.locals import *
from vec2d import *
from math import sqrt, e, log
from random import uniform, normalvariate
import simple_font_manager
from euclid import Circle, Line2, LineSegment2, Point2
from collections import defaultdict
#import psyco

def draw_binding( surface, circle_pos, points ):
	#compute angle of every line from circle center to each point
	if len(points) < 2:
		return
	#print "circle center:", circle_pos
	radius = (circle_pos - points[0]).get_length()
	#print "radius:", radius
	angles = [-((p-circle_pos).get_rad_angle()) for p in points]
	#print "angles:", angles
	#convert all angles to positive
	max_span = 2*math.pi
	for i,angle in enumerate(angles):
		#test which is the best starting angle
		relative = []
		for angle2 in angles:
			if angle2 >= angle:
				relative.append( angle2 - angle )
			else:
				relative.append( 2*math.pi+angle2 - angle )
		span = max(relative)
		if span < max_span:
			max_span = span
			start_angle = angle
			final_angle = span+angle
	pygame.draw.arc( surface, (0,0,0), Rect(circle_pos-(radius,radius), vec2d(radius,radius)*2),
					start_angle, final_angle)
	#take min and max,

def line_circle_intersection( arc, circle_pos, circle_radius, inset=True): 
	circ = Circle(Point2(circle_pos[0], circle_pos[1]), float(circle_radius))
	p1 = Point2(arc.source_pos[0], arc.source_pos[1])
	p2 = Point2(arc.target_pos[0], arc.target_pos[1])
	if p1 != p2:
		line = Line2(p1, p2)
		inters = line.intersect( circ )
		if (abs((p2 - inters.p1).magnitude() - (p2 - inters.p2).magnitude()) > 
			abs((p1 - inters.p1).magnitude() - (p1 - inters.p2).magnitude())):
			p = p2
		else:
			p = p1
		if (p - inters.p1).magnitude() > (p - inters.p2).magnitude():
			return vec2d( inters.p2.x, inters.p2.y ) #use p2
		return vec2d( inters.p1.x, inters.p1.y ) #use p1
	else:
		# circle to ellipse intersection
		if arc.r_a != arc.r_b:
			delta = sqrt(arc.r_b**2*(arc.r_a**4-arc.r_a**2*arc.r_b**2+arc.r_b**2*circle_radius**2))
			y = ((circle_pos[1]-circle_radius)*arc.r_a**2+delta-arc.r_b**2*circle_pos[1])/(arc.r_a**2-arc.r_b**2)
			if inset:
				x = circle_pos[0]-sqrt(circle_radius**2-(y-circle_pos[1])**2)
			else:
				x = circle_pos[0]+sqrt(circle_radius**2-(y-circle_pos[1])**2)
			return vec2d(x, y)
		return circle_pos+(circle_radius,0) #dummy

#single node
class node:
	def __init__(self, x, label=''):
		self.x = x #position
		self.oldx = x #old position
		self.a = 0 #force accumulators
		self.label = label
		self.radius = 20
		
		self.marked= False #for bfs
		self.color = (int(uniform(0,150)), int(uniform(0,150)), int(uniform(0,150)))
		self.numNodes=0 #num of nodes this is connected to. filled in countNodes()
		
#single spring
class spring:
	def __init__(self, n1, n2, displace=False, k = -60, restDist = 100):
		self.n1 = n1
		self.n2 = n2
		self.k = k
		self.rest = restDist
		self.displace = displace
		self.compute_coordinates()
	
	def compute_coordinates(self):
		"""computes beginning and end points"""
		self.source_pos = vec2d(self.n1.x)
		self.target_pos = vec2d(self.n2.x)
		#compute intersection points
		if self.source_pos != self.target_pos:
			if self.displace:
				delta = (self.target_pos - self.source_pos).perpendicular().normalized()
				self.source_pos += delta*5
				self.target_pos += delta*5
			circ = Circle(Point2(self.n1.x[0], self.n1.x[1]), float(self.n1.radius))
			p1 = Point2(self.source_pos[0], self.source_pos[1])
			p2 = Point2(self.target_pos[0], self.target_pos[1])
			line = Line2(p1, p2)
			inters = line.intersect( circ )
			if (p2 - inters.p1).magnitude() > (p2 - inters.p2).magnitude():
				#use p2
				self.source_pos[0] = inters.p2.x
				self.source_pos[1] = inters.p2.y
			else:
				#use p1
				self.source_pos[0] = inters.p1.x
				self.source_pos[1] = inters.p1.y
			circ = Circle(Point2(self.n2.x[0], self.n2.x[1]), float(self.n2.radius))
			inters = line.intersect( circ )
			if (p1 - inters.p1).magnitude() > (p1 - inters.p2).magnitude():
				#use p2
				self.target_pos[0] = inters.p2.x
				self.target_pos[1] = inters.p2.y
			else:
				#use p1
				self.target_pos[0] = inters.p1.x
				self.target_pos[1] = inters.p1.y
				
	def draw( self, surface ):
		self.r_a = 15
		self.r_b = 25
		if self.source_pos != self.target_pos:
			pygame.draw.aaline(surface, (0,0,0), 
								self.source_pos.inttup(), self.target_pos.inttup(), 1)
			#arrow
			vect = ((self.target_pos - self.source_pos).normalized()*10).rotated(135)
			#print vect
			pygame.draw.aaline(surface, (0,0,0), 
								self.target_pos.inttup(), (self.target_pos+vect).inttup(), 1)
			vect = ((self.target_pos - self.source_pos).normalized()*10).rotated(-135)
			pygame.draw.aaline(surface, (0,0,0), 
								self.target_pos.inttup(), (self.target_pos+vect).inttup(), 1)
		else:
			ellipse_center = self.source_pos-(0,self.r_b)
			inter1 = line_circle_intersection( self, self.n1.x, self.n1.radius, inset=False )
			inter2 = line_circle_intersection( self, self.n1.x, self.n1.radius, inset=True )
			#compute angles
			#print "Ellipse:", ellipse_center
			#pygame.draw.circle( surface, (255,0,0), ellipse_center.inttup(), 2, 0)
			#print "Inter1:", inter1, "Inter2:", inter2
			#pygame.draw.circle( surface, (255,0,0), inter1.inttup(), 2, 0)
			#pygame.draw.circle( surface, (255,0,0), inter2.inttup(), 2, 0)
			dy = -sqrt((1-1/self.r_a**2)*self.r_b**2*(inter2[0]-ellipse_center[0])**2)/(inter2[0]-ellipse_center[0])
			tangent = vec2d(1,dy)
			start_angle = -((inter1-ellipse_center).get_rad_angle())
			end_angle = 2*math.pi-((inter2-ellipse_center).get_rad_angle())
			#print "Start angle:", start_angle, "End angle:", end_angle
			pygame.draw.arc( surface, (0,0,0), 
					Rect(self.source_pos-(self.r_a,self.r_b*2), vec2d(self.r_a, self.r_b)*2),
					start_angle, end_angle)
			vect = (tangent.normalized()*10).rotated(135)
			#print vect
			pygame.draw.aaline(surface, (0,0,0), 
								inter2.inttup(), (inter2+vect).inttup(), 1)
			vect = (tangent.normalized()*10).rotated(-135)
			pygame.draw.aaline(surface, (0,0,0), 
								inter2.inttup(), (inter2+vect).inttup(), 1)
		
class ForceDirectedGraph:
	"""Represents a force directed graph allowing interactive manipulation"""
	def __init__(self, node_labels=[], insets={}, outsets={}):
	
		#psyco.full()
		
		self.w = 700
		self.h = 700
		pygame.init()
		self.screen = pygame.display.set_mode((self.w, self.h))
		self.screen.fill((0,0,0))
		self.font_mgr = simple_font_manager.cFontManager(((None, 12), ('arial', 12), ('arial', 24)))
		
		#PHYSICS
		self.dt = 0.01 #time step
		self.friction = 0.05
		
		#lists of nodes and springs
		self.node_labels = node_labels
		self.insets = insets
		self.outsets = outsets
		self.nodes = []
		self.springs = []		
		self.dragging = None #is user dragging a node?
		
		self.selected = None #selected node
		self.physics = True #is physics enabled?
		
		self.c = 0 #program counter used in main loop
		
	def verlet(self):
		"""integrate one single time step to get new positions 
		from old positions based on acceleration of each node."""
		for n in self.nodes:
			temp = vec2d(n.x.x, n.x.y) #store old position
			n.x += (1.0 - self.friction)*n.x - (1.0 - self.friction)*n.oldx + n.a*self.dt*self.dt
			n.oldx = temp
		
		for n in self.nodes: #reset accelerations for next iteration
			n.a = 0.0
			
	
	def accumulate_force(self):
		"""accumulate all the forces between all the nodes"""
		#REPELL NODES CLOSE TO OTHER NODES
		#proportional to their separation in graph
		#Nodes are close => big attraction
		#Nodes are far => no attraction
		for n1 in self.nodes:
			for n2 in self.nodes:
				d=self.paths[(n1,n2)]	#distance in graph btw n1 and n2
				dst =n1.x.get_distance(n2.x) #distance on actual layout
				if d > 1 and  dst< 200:
					dp = n2.x - n1.x #get vector from n1->n2
					dp.length = 2000/d #set its length to strength of interaction
					n2.a += dp #add that vector to both acceleration of n1 and n2
					n1.a += -dp		
			
		#SPRING STUFF
		for s in self.springs:
			dp = s.n2.x - s.n1.x #get vector pointing from n1->n2
			
			if dp.length != 0:
				dx = dp.length - s.rest #get the displacement from rest length
				dp.length = s.k*dx #multiply by spring contant
				s.n2.a += dp #add the vector to each n1 and n2 accelerations
				s.n1.a += -dp
			
	def net_movement(self):
		"""return the net movement of all nodes.
		if there is very little movement then the simulation
		can be stopped and result returned"""
		a=0.0
		for n in self.nodes:
			a+= (n.x - n.oldx).length
		return a
		
	def handle_input(self):
		"""handle all user input and interactivity"""
		for event in pygame.event.get():
			if event.type == QUIT:
				self.quit()
			elif event.type == KEYDOWN:
				if event.key == K_ESCAPE:
					self.quit()
				elif event.key == K_r:
					self.init_nodes()
					self.do_bfs()
					self.do_count()
				elif event.key == K_d:
					#delete closest node
					d = self.findclosest(pygame.mouse.get_pos())
					toRem = []
					for s in self.springs:
						if s.n1 == d or s.n2 == d:
							toRem.append(s)
					for t in toRem:
						self.springs.remove(t)
					self.nodes.remove(d)
					self.do_bfs()
					self.do_count()
				elif event.key == K_p:
					self.physics = not self.physics
				elif event.key == K_n:
					for z in self.nodes:
						z.x = vec2d(uniform(self.w/2-10,self.w/2+10), uniform(self.h/2-10,self.h/2+10))
						z.oldx = z.x
					
			elif event.type == MOUSEBUTTONUP:
				if event.button == 1:
					self.dragging = None
				else:
					now = vec2d(event.pos)
					then = vec2d(self.selected)
					if now.get_distance(then) < 10:
						#just make a new node here (at now)
						self.nodes.append(node(now))
						self.do_bfs()
						self.do_count()
					else:
						#make new line btw last node and this node
						nowNode=self.findclosest(now)
						thenNode=self.findclosest(then)
						self.springs.append(spring(nowNode, thenNode))
						self.do_bfs()
						self.do_count()
											
					self.selected = None
					
			elif event.type == MOUSEBUTTONDOWN:
				if event.button == 1:
					self.dragging = self.findclosest(event.pos)
				else:
					self.selected = event.pos
					
	#find the closest node to position p. p is a vec2d
	def findclosest(self, p):
		ld = self.w + self.h
		li = None
		v = vec2d(p)
		for n in self.nodes:
			d = v.get_distance(n.x) 
			if d < ld:
				ld = d
				li = n
		return li
		
	def draw(self):
		"""draw all springs and nodes"""
		white = (255,255,255)
		black = (0,0,0)
		self.screen.fill( white )
		arc_dict = {}
		rect = pygame.Rect((0,0), (30, self.w))
		legend = 'p-toggle physics '
		if self.physics:
			legend += 'off'
		else:
			legend += 'on'
		legend += ' || <Esc>-quit || n-randomize positions || d-delete node'
		self.font_mgr.Draw(self.screen, 'arial', 12, legend,
								rect, black, 'left', 'top', True)
		for s in self.springs:
			arc_dict[(s.n1.label,s.n2.label)] = s
			s.compute_coordinates()
			s.draw( self.screen )
			
		for n in self.nodes:
			#pygame.draw.circle(self.screen, white, n.x.inttup(), n.radius, 0)
			pygame.draw.circle(self.screen, black, n.x.inttup(), n.radius, 1)
			rect = pygame.Rect((n.x-vec2d(n.radius/2,n.radius/2)).inttup(), (n.radius, n.radius))
			self.font_mgr.Draw(self.screen, 'arial', 24, n.label,
								rect, black, 'center', 'center', True)
		
		for s_act, outsets in self.outsets.iteritems():
			radius = 30
			#level = defaultdict(int)
			sorted_outsets = sorted(outsets,key=len)
			last_single = True
			for outset in sorted_outsets:
				#max_level = max([level[t_act] for t_act in outset])
				points = []
				if last_single and len(outset) > 1:
					radius += 10
				for t_act in outset:
					#level[t_act] += 1
					arc = arc_dict[(s_act,t_act)]
					circle_center = arc.n1.x
					#inter = line_circle_intersection( arc, circle_center, radius+max_level*10.0 )
					inter = line_circle_intersection( arc, circle_center, radius, inset=False  )
					points.append( inter )
					pygame.draw.circle(self.screen, black, inter.inttup(), 5, 0)
					#pygame.gfxdraw.aacircle(self.screen, inter.inttup(), 5, black)
				draw_binding( self.screen, circle_center, points )
				if len(outset) > 1:
					last_single = False
					radius += 10
		for t_act, insets in self.insets.iteritems():
			radius = 35
			#level = defaultdict(int)
			sorted_insets = sorted(insets,key=len)
			last_single = True
			for inset in sorted_insets:
				#max_level = max([level[s_act] for s_act in inset])
				points = []
				if last_single and len(inset) > 1:
					radius += 10
				for s_act in inset:
					#level[s_act] += 1
					arc = arc_dict[(s_act,t_act)]
					circle_center = arc.n2.x
					#inter = line_circle_intersection( arc, arc.n2.x, radius+max_level*10.0 )
					inter = line_circle_intersection( arc, circle_center, radius, inset=True )
					points.append( inter )
					pygame.draw.circle(self.screen, black, inter.inttup(), 5, 0)
				draw_binding( self.screen, circle_center, points )
				if len(inset) > 1:
					last_single = False
					radius += 10
		#draw insets and outsets
		
		pygame.display.flip()
	
	def dnc(self, k, l):
		"""true if there is no spring yet between the k'th and l'th node"""
		i=self.nodes[k]
		j=self.nodes[l]
		for s in self.springs:
			if (s.n1==i and s.n2==j) or (s.n1==j and s.n2==i):
				return False
		return True
	
	def init_nodes(self):
		"""initialize all the nodes and springs"""
		self.nodes=[]
		self.springs=[]
		
		num_nodes = len(self.node_labels)
		node_dict = {}
		#put nodes in max distance order to initial activity
		for n in self.node_labels:
			if len(self.insets[n]) == 0: #initial activity
				x_pos = self.w/2-15
				y_pos = self.h/2
			elif len(self.outsets[n]) == 0: #final activity
				x_pos = self.w/2+15
				y_pos = self.h/2
			else: # rest of nodes
				x_pos = uniform(self.w/2-10,self.w/2+10)
				y_pos = uniform(self.h/2-10,self.h/2+10)
			z=node(vec2d(x_pos, y_pos), n)
			node_dict[n] = z
			self.nodes.append(z)
		
		arcs = set()
		for s_act, outsets in self.outsets.iteritems():
			for outset in outsets:
				for t_act in outset:
					arcs.add( (s_act,t_act) )
		for s_act, t_act in arcs:
			s = spring(node_dict[s_act], node_dict[t_act], (t_act, s_act) in arcs )
			self.springs.append(s)
#		for i in range(num_nodes):
#			for j in range(num_nodes):
#				if i != j and uniform(0,1) < 0.1 and self.dnc(i,j):
#					s = spring(self.nodes[i], self.nodes[j])
#					self.springs.append(s)
					
		self.c = 0
		
	
	def do_bfs(self):
		"""do a BFS search to create the dictionary containing the length of the
		shortest path between any two nodes in the graph, along springs	"""
		#construct the initial dict
		self.paths={}
		for n in self.nodes:
			for n2 in self.nodes:
				if n == n2:
					self.paths[(n,n2)] = 0
				else:
					self.paths[(n,n2)] = 10 #10 if they arent connected
			
		#now run BFS on each node to find the right values and fill them in
		for n in self.nodes:
			lst=[n]
			d=1
			for n2 in self.nodes: #reset nodes
				n2.marked = False
				
			while len(lst) > 0:
				nn = lst[0]
				del lst[0]
				nn.marked = True
				
				for s in self.springs:
					n2 = None
					if s.n1 == nn:
						n2 = s.n2
					elif s.n2 == nn:
						n2 = s.n1
						
					if n2 != None and n2.marked == False:
						#nn is part of this spring
						#we found n2 in depth d from n
						self.paths[(n,n2)] = min(d, self.paths[(n,n2)])
						self.paths[(n2,n)]= min(d, self.paths[(n2,n)])
						n2.color = nn.color
						
						#append n2 to the lst
						lst.append(n2)
						
				d+=1 #increment depth
	
	
	def do_count(self):
		"""count number of connections for each node
		return the highest number of connections of any node"""
		maxN = 0
		
		for n in self.nodes:
			k=0
			for s in self.springs:
				if s.n1 == n or s.n2 == n:
					k+=1
			n.numNodes=k/2 #k/2 because graph is undirected. nodes are doublecounted
			if k/2 > maxN:
				maxN = k/2
		
		#now set the spring constants appropriately
		for s in self.springs:
			n=max(s.n1.numNodes, s.n2.numNodes)
			s.rest=100+n*20
			
		return maxN
		
	
	def run(self):	
		"""main method. do the simulation"""
		
		#initialize the particle system
		self.init_nodes()
		self.do_bfs()
		self.do_count()
		self.keep_running = True
		
		while self.keep_running:	
			self.c +=1
				
			#simulate until net movement is very low, but
			#at least for 100 time steps
			#also simulate if user is dragging a node
			nm = self.net_movement()
			if nm > -0.5 or self.c < 100 or self.dragging:
				#if physics is enabled then do simulation
				if self.physics: 
					self.accumulate_force()
					self.verlet()
			
			self.handle_input() #handle all user input
			
			#handle node dragging
			if not self.dragging == None:
				pos = pygame.mouse.get_pos()
				self.dragging.x = vec2d(pos)
				self.dragging.oldx = vec2d(pos)
				
			#draw everything
			self.draw()
		pygame.quit()
			
	def quit(self):
		#sys.exit(1)
		#pygame.quit()
		self.keep_running = False

if __name__ == "__main__":
	s = ForceDirectedGraph()
	s.run()